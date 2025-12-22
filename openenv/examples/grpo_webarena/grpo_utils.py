"""GRPO Utilities for WebArena/BrowserGym Training with TorchForge."""

import asyncio
import re
import uuid
from dataclasses import dataclass

import torch
import torch.nn.functional as F
import torchstore as ts

from envs.browsergym_env import BrowserGymAction, BrowserGymEnv
from forge.util.checkpoint import drop_weights
from forge.actors.generator import Generator
from forge.actors.reference_model import ReferenceModel
from forge.actors.replay_buffer import ReplayBuffer
from forge.actors.trainer import TitanTrainer
from forge.controller.actor import ForgeActor
from forge.controller.provisioner import init_provisioner, shutdown
from forge.observability.metric_actors import get_or_create_metric_logger
from forge.types import LauncherConfig, ProvisionerConfig
from forge.util.ops import compute_logprobs
from monarch.actor import endpoint
from vllm.transformers_utils.tokenizer import get_tokenizer


MAX_STEPS = 15
ACTION_RE = re.compile(r"[a-z_]+\s*\([^)]*\)", re.IGNORECASE)


@dataclass
class Episode:
    episode_id: str
    pad_id: int
    request_len: int
    response_len: int
    task_id: str
    step_num: int
    completion: object = None
    ref_logprobs: torch.Tensor = None
    reward: float = None
    advantage: float = None

    @property
    def policy_version(self):
        return self.completion.generator_version

    @property
    def request_tensor(self):
        t = self.completion.prompt_ids.to(torch.long)
        if t.shape[0] < self.request_len:
            t = F.pad(t, (self.request_len - t.shape[0], 0), value=self.pad_id)
        return t

    @property
    def response_tensor(self):
        t = self.completion.token_ids.to(torch.long)
        if t.shape[0] < self.response_len:
            t = F.pad(t, (0, self.response_len - t.shape[0]), value=self.pad_id)
        return t


Group = list[Episode]


def collate(batches):
    inputs, targets = [], []
    for batch in batches:
        req = torch.stack([e.request_tensor for e in batch])
        res = torch.stack([e.response_tensor for e in batch])
        ref = torch.stack([e.ref_logprobs for e in batch]).squeeze()
        adv = torch.tensor([e.advantage for e in batch]).unsqueeze(-1)
        mask = res != batch[0].pad_id
        inputs.append({"tokens": torch.cat([req, res], dim=1)})
        targets.append({"response": res, "ref_logprobs": ref, "advantages": adv, "padding_mask": mask})
    return inputs, targets


def simple_grpo_loss(logits, response, ref_logprobs, advantages, padding_mask, beta=0.1):
    logprobs = compute_logprobs(logits, response)
    kl = torch.exp(ref_logprobs - logprobs) - (ref_logprobs - logprobs) - 1
    policy_loss = torch.exp(logprobs - logprobs.detach()) * advantages
    per_token = -(policy_loss - beta * kl)
    return ((per_token * padding_mask).sum(1) / padding_mask.sum(1).clamp(min=1)).mean()


SYSTEM_PROMPT = """You are a web navigation agent. Output a single action command.
Actions: click('id'), fill('id', 'text'), scroll('up'/'down'), noop()
Output ONLY the action, nothing else."""


def format_prompt(goal, url, axtree, history, step, tokenizer):
    axtree = axtree[:4000] + "..." if len(axtree) > 4000 else axtree
    user = f"GOAL: {goal}\nURL: {url}\nPAGE:\n{axtree}\n"
    if history:
        user += "HISTORY: " + ", ".join(history[-5:]) + "\n"
    user += f"Step {step+1}/{MAX_STEPS}. Action?"
    return tokenizer.apply_chat_template(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
        tokenize=False, add_generation_prompt=True
    )


def parse_action(text):
    m = ACTION_RE.search(text or "")
    return m.group(0).strip() if m else "noop()"


@dataclass
class WebArenaReward(ForgeActor):
    @endpoint
    async def evaluate(self, reward, success, steps):
        if success:
            return 2.0 + max(0, (MAX_STEPS - steps) / MAX_STEPS)
        return 1.0 + reward if reward > 0 else (-0.1 if reward == 0 else -0.5)


@dataclass
class ComputeAdvantages(ForgeActor):
    @endpoint
    async def compute(self, group: Group):
        r = torch.tensor([[e.reward for e in group]])
        return ((r - r.mean(1, keepdim=True)) / (r.std(1, keepdim=True) + 1e-4)).squeeze(0).tolist()


@dataclass
class EnvActor(ForgeActor):
    model: str = "meta-llama/Llama-3.1-8B-Instruct"

    @endpoint
    async def setup(self):
        self._tok = get_tokenizer(self.model)

    @endpoint
    async def tokenizer(self):
        return self._tok

    @endpoint
    async def pad_token(self):
        return self._tok.pad_token_id or self._tok.eos_token_id


_env_cache = {}


def get_env(url):
    if url not in _env_cache:
        _env_cache[url] = BrowserGymEnv(base_url=url)
    return _env_cache[url]


async def play_episode(idx, task_id, url, policy, tokenizer):
    env = get_env(url)
    result = env.reset()
    obs, done, step, history, steps = result.observation, False, 0, [], []

    while not done and step < MAX_STEPS:
        prompt = format_prompt(obs.goal, obs.url, obs.axtree_txt or obs.text, history, step, tokenizer)
        responses = await policy.generate.route(prompt)
        action = parse_action(responses[0].text)
        history.append(action)
        steps.append({"step": step, "prompt": prompt, "response": responses[0], "action": action})
        result = env.step(BrowserGymAction(action_str=action))
        obs, done = result.observation, result.done
        step += 1

    reward = result.reward or 0
    success = reward > 0.5
    return [{"task_id": task_id, "reward": reward, "success": success, "total": len(steps), **s} for s in steps]


class GRPOTrainer:
    def __init__(self, services, cfg):
        self._svc = services
        self._cfg = cfg
        self._stop = asyncio.Event()

    @property
    def policy(self):
        return self._svc['policy']

    async def run(self, steps):
        policy = self._svc['policy']
        trainer = self._svc['trainer']
        buffer = self._svc['buffer']
        advantages = self._svc['advantages']
        ref = self._svc['ref']
        reward = self._svc['reward']
        tok = self._svc['tokenizer']
        pad = self._svc['pad']
        mlog = self._svc['mlogger']

        group_size = self._cfg.group_size
        req_len = self._cfg.max_req_tokens
        res_len = self._cfg.max_res_tokens
        url = self._cfg.get("webarena_env", {}).get("server_url", "http://localhost:8005")

        async def rollouts():
            n = 0
            while not self._stop.is_set():
                all_steps = []
                for i in range(group_size):
                    all_steps.extend(await play_episode(i, str(uuid.uuid4())[:8], url, policy, tok))

                episodes = []
                ids = torch.ones((len(all_steps), req_len + res_len), dtype=torch.long)
                for i, s in enumerate(all_steps):
                    ep = Episode(str(uuid.uuid4()), pad, req_len, res_len, s["task_id"], s["step"], s["response"])
                    ep.reward = await reward.evaluate.route(s["reward"], s["success"], s["total"])
                    episodes.append(ep)
                    ids[i, :req_len] = ep.request_tensor
                    ids[i, req_len:] = ep.response_tensor

                refs = await ref.forward.route(ids, req_len, return_logprobs=True)
                for i, ep in enumerate(episodes):
                    ep.ref_logprobs = refs[i]

                advs = await advantages.compute.call_one(episodes)
                for ep, a in zip(episodes, advs):
                    ep.advantage = a
                    await buffer.add.call_one(ep)

                n += 1
                print(f"Rollout {n}: {len(episodes)} steps")

        async def train():
            step = 0
            while step < steps:
                batch = await buffer.sample.call_one(curr_policy_version=step)
                if not batch:
                    await asyncio.sleep(0.1)
                    continue
                await trainer.train_step.call(*batch)
                step += 1
                await trainer.push_weights.call(step)
                await policy.update_weights.fanout(step)
                if step >= 2:
                    await drop_weights(step - 1)
                await mlog.flush.call_one(step)
                print(f"Step {step}/{steps}")

        roll = asyncio.create_task(rollouts())
        try:
            await train()
        finally:
            self._stop.set()
            roll.cancel()

    async def shutdown(self):
        await shutdown()


async def setup_training(config_path: str):
    from omegaconf import OmegaConf
    cfg = OmegaConf.load(config_path)

    prov = await init_provisioner(
        ProvisionerConfig(launcher_config=LauncherConfig(**cfg.provisioner)) if cfg.get("provisioner") else None
    ) if cfg.get("provisioner") else await init_provisioner()

    mlog = await get_or_create_metric_logger()
    await mlog.init_backends.call_one(cfg.get("metric_logging", {"console": {"logging_mode": "global_reduce"}}))

    env, policy, trainer, buffer, adv, ref, reward = await asyncio.gather(
        EnvActor.options(**cfg.actors.get("webarena_env", {})).as_actor(**cfg.get("webarena_env", {})),
        Generator.options(**cfg.services.policy).as_service(**cfg.policy),
        TitanTrainer.options(**cfg.actors.trainer).as_actor(**cfg.trainer, loss=simple_grpo_loss),
        ReplayBuffer.options(**cfg.actors.replay_buffer).as_actor(**cfg.replay_buffer, collate=collate),
        ComputeAdvantages.options(**cfg.actors.compute_advantages).as_actor(),
        ReferenceModel.options(**cfg.services.ref_model).as_service(**cfg.ref_model),
        WebArenaReward.options(**cfg.services.reward_actor).as_service(),
    )

    hosts = prov.get_host_mesh(cfg.actors.trainer["mesh_name"])
    await ts.initialize(mesh=hosts.spawn_procs(per_host={"procs": cfg.actors.trainer["procs"]}), strategy=ts.LocalRankStrategy())

    await env.setup.call_one()
    tok = await env.tokenizer.call_one()
    pad = await env.pad_token.call_one()

    return GRPOTrainer({
        'policy': policy, 'trainer': trainer, 'buffer': buffer, 'advantages': adv,
        'ref': ref, 'reward': reward, 'tokenizer': tok, 'pad': pad, 'mlogger': mlog
    }, cfg)

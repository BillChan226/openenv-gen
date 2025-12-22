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

# Logging verbosity: 0=minimal, 1=episode summaries, 2=step details
LOG_LEVEL = 2


def log(msg, level=1):
    if level <= LOG_LEVEL:
        print(msg)


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
    """GRPO loss with KL penalty. Returns scalar loss."""
    logprobs = compute_logprobs(logits, response)
    kl = torch.exp(ref_logprobs - logprobs) - (ref_logprobs - logprobs) - 1
    policy_loss = torch.exp(logprobs - logprobs.detach()) * advantages
    per_token = -(policy_loss - beta * kl)
    loss = ((per_token * padding_mask).sum(1) / padding_mask.sum(1).clamp(min=1)).mean()

    # Log training metrics
    with torch.no_grad():
        log(f"  [Loss] loss={loss.item():.4f} kl={kl.mean().item():.4f} adv_mean={advantages.mean().item():.4f}", 1)

    return loss


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
    """Get or create cached env. Env operations are SYNC (run in main thread)."""
    if url not in _env_cache:
        _env_cache[url] = BrowserGymEnv(base_url=url)
    return _env_cache[url]


async def play_episode(idx, task_id, url, policy, tokenizer):
    """Play one episode.

    SYNC: env.reset(), env.step() - BrowserGym/Playwright runs synchronously
    ASYNC: policy.generate.route() - vLLM inference is async via TorchForge
    """
    env = get_env(url)

    # SYNC: Reset environment
    result = env.reset()
    obs, done, step, history, steps = result.observation, False, 0, [], []

    log(f"\n{'='*60}", 1)
    log(f"[Episode {idx}] task={task_id} goal={obs.goal[:80]}...", 1)
    log(f"{'='*60}", 1)

    while not done and step < MAX_STEPS:
        # Log raw observation
        log(f"\n[Step {step+1}/{MAX_STEPS}]", 2)
        log(f"  [Obs] url={obs.url}", 2)
        log(f"  [Obs] axtree_len={len(obs.axtree_txt or obs.text)} chars", 2)

        # Format prompt
        prompt = format_prompt(obs.goal, obs.url, obs.axtree_txt or obs.text, history, step, tokenizer)
        log(f"  [Prompt] {len(prompt)} chars", 2)

        # ASYNC: Generate action from policy (vLLM inference)
        responses = await policy.generate.route(prompt)
        raw_output = responses[0].text

        # Parse action
        action = parse_action(raw_output)

        # Log model output
        log(f"  [Model Output] {raw_output!r}", 2)
        log(f"  [Parsed Action] {action}", 2)

        history.append(action)
        steps.append({"step": step, "prompt": prompt, "response": responses[0], "action": action})

        # SYNC: Execute action in environment
        result = env.step(BrowserGymAction(action_str=action))
        obs, done = result.observation, result.done
        step += 1

    reward = result.reward or 0
    success = reward > 0.5

    log(f"\n[Episode End] steps={len(steps)} reward={reward:.2f} success={success}", 1)

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
            """Rollout loop - runs episodes and fills replay buffer.

            ASYNC operations:
            - play_episode() contains async policy.generate
            - reward.evaluate.route() - reward computation
            - ref.forward.route() - reference model forward pass
            - advantages.compute.call_one() - advantage computation
            - buffer.add.call_one() - add to replay buffer
            """
            n = 0
            while not self._stop.is_set():
                log(f"\n{'#'*60}", 1)
                log(f"# ROLLOUT {n+1}", 1)
                log(f"{'#'*60}", 1)

                # Play episodes (sequentially within group for now)
                all_steps = []
                for i in range(group_size):
                    episode_steps = await play_episode(i, str(uuid.uuid4())[:8], url, policy, tok)
                    all_steps.extend(episode_steps)

                # Process all steps into episodes
                episodes = []
                ids = torch.ones((len(all_steps), req_len + res_len), dtype=torch.long)

                for i, s in enumerate(all_steps):
                    ep = Episode(str(uuid.uuid4()), pad, req_len, res_len, s["task_id"], s["step"], s["response"])
                    # ASYNC: Compute shaped reward
                    ep.reward = await reward.evaluate.route(s["reward"], s["success"], s["total"])
                    episodes.append(ep)
                    ids[i, :req_len] = ep.request_tensor
                    ids[i, req_len:] = ep.response_tensor

                # ASYNC: Get reference model log probabilities (for KL penalty)
                log(f"\n[Ref Model] Computing logprobs for {len(episodes)} steps...", 1)
                refs = await ref.forward.route(ids, req_len, return_logprobs=True)
                for i, ep in enumerate(episodes):
                    ep.ref_logprobs = refs[i]

                # ASYNC: Compute group advantages
                advs = await advantages.compute.call_one(episodes)
                log(f"[Advantages] mean={sum(advs)/len(advs):.4f} min={min(advs):.4f} max={max(advs):.4f}", 1)

                # ASYNC: Add to replay buffer
                for ep, a in zip(episodes, advs):
                    ep.advantage = a
                    await buffer.add.call_one(ep)

                n += 1
                rewards = [ep.reward for ep in episodes]
                log(f"\n[Rollout {n} Summary] episodes={group_size} steps={len(episodes)} "
                    f"reward_mean={sum(rewards)/len(rewards):.4f}", 0)

        async def train():
            """Training loop - samples from buffer and updates policy.

            ASYNC operations:
            - buffer.sample.call_one() - sample batch from replay buffer
            - trainer.train_step.call() - forward/backward pass
            - trainer.push_weights.call() - save weights to store
            - policy.update_weights.fanout() - broadcast weights to all replicas
            - drop_weights() - cleanup old checkpoints
            - mlog.flush.call_one() - flush metrics
            """
            step = 0
            while step < steps:
                # ASYNC: Sample batch from replay buffer
                batch = await buffer.sample.call_one(curr_policy_version=step)
                if not batch:
                    await asyncio.sleep(0.1)
                    continue

                log(f"\n{'='*60}", 0)
                log(f"[Train Step {step+1}/{steps}]", 0)

                # ASYNC: Training step (forward + backward + optimizer step)
                await trainer.train_step.call(*batch)
                step += 1

                # ASYNC: Push new weights to distributed store
                await trainer.push_weights.call(step)

                # ASYNC: Fanout weight update to all policy replicas
                await policy.update_weights.fanout(step)

                # Cleanup old weights (keep memory bounded)
                if step >= 2:
                    await drop_weights(step - 1)

                # ASYNC: Flush metrics
                await mlog.flush.call_one(step)

                log(f"[Train Step {step}/{steps}] completed", 0)

        # Run rollouts and training concurrently
        log("\n" + "="*60, 0)
        log("Starting GRPO Training", 0)
        log(f"  - Group size: {group_size}", 0)
        log(f"  - Max steps per episode: {MAX_STEPS}", 0)
        log(f"  - Training steps: {steps}", 0)
        log(f"  - Server URL: {url}", 0)
        log("="*60 + "\n", 0)

        roll = asyncio.create_task(rollouts())
        try:
            await train()
        finally:
            self._stop.set()
            roll.cancel()

    async def shutdown(self):
        await shutdown()


async def setup_training(config_path: str):
    """Setup all TorchForge actors and services.

    All setup operations are ASYNC - they spawn distributed actors.
    """
    from omegaconf import OmegaConf
    cfg = OmegaConf.load(config_path)

    log(f"Loading config from {config_path}", 0)

    # ASYNC: Initialize provisioner (manages distributed resources)
    prov = await init_provisioner(
        ProvisionerConfig(launcher_config=LauncherConfig(**cfg.provisioner)) if cfg.get("provisioner") else None
    ) if cfg.get("provisioner") else await init_provisioner()

    # ASYNC: Setup metric logger
    mlog = await get_or_create_metric_logger()
    await mlog.init_backends.call_one(cfg.get("metric_logging", {"console": {"logging_mode": "global_reduce"}}))

    log("Spawning actors and services...", 0)

    # ASYNC: Spawn all actors/services in parallel
    env, policy, trainer, buffer, adv, ref, reward = await asyncio.gather(
        EnvActor.options(**cfg.actors.get("webarena_env", {})).as_actor(**cfg.get("webarena_env", {})),
        Generator.options(**cfg.services.policy).as_service(**cfg.policy),
        TitanTrainer.options(**cfg.actors.trainer).as_actor(**cfg.trainer, loss=simple_grpo_loss),
        ReplayBuffer.options(**cfg.actors.replay_buffer).as_actor(**cfg.replay_buffer, collate=collate),
        ComputeAdvantages.options(**cfg.actors.compute_advantages).as_actor(),
        ReferenceModel.options(**cfg.services.ref_model).as_service(**cfg.ref_model),
        WebArenaReward.options(**cfg.services.reward_actor).as_service(),
    )

    # ASYNC: Initialize TorchStore for weight synchronization
    hosts = prov.get_host_mesh(cfg.actors.trainer["mesh_name"])
    await ts.initialize(mesh=hosts.spawn_procs(per_host={"procs": cfg.actors.trainer["procs"]}), strategy=ts.LocalRankStrategy())

    # ASYNC: Setup tokenizer
    await env.setup.call_one()
    tok = await env.tokenizer.call_one()
    pad = await env.pad_token.call_one()

    log("Setup complete!", 0)

    return GRPOTrainer({
        'policy': policy, 'trainer': trainer, 'buffer': buffer, 'advantages': adv,
        'ref': ref, 'reward': reward, 'tokenizer': tok, 'pad': pad, 'mlogger': mlog
    }, cfg)

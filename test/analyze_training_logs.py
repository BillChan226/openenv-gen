#!/usr/bin/env python3
"""
Training Log Analyzer for GRPO Web Agent Training

This script parses training logs from /scratch/czr/env-gen/logs/training.logs
and extracts evaluation results at each evaluation stage (every 5 steps).

Key features:
- Parse all evaluation stages
- Extract task-level results (success/failure, reward, actions)
- Track task performance across training steps
- Identify tasks that improved (failed before, succeeded later)
- Generate summary statistics
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


@dataclass
class TaskResult:
    """Represents a single task evaluation result."""
    task_id: str
    task_num: int
    rollout_num: int
    benchmark: str
    task_type: str
    goal: str
    initial_url: str
    success: bool
    reward: float
    task_length: int
    actions: List[str]
    has_action_error: bool = False


@dataclass
class EvaluationStage:
    """Represents an evaluation stage at a specific training step."""
    step: int
    num_tasks: int
    task_pool_size: int
    results: List[TaskResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.success) / len(self.results)

    @property
    def avg_reward(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.reward for r in self.results) / len(self.results)

    @property
    def successful_tasks(self) -> List[TaskResult]:
        return [r for r in self.results if r.success]

    @property
    def failed_tasks(self) -> List[TaskResult]:
        return [r for r in self.results if not r.success]


class TrainingLogAnalyzer:
    """Analyzes training logs and extracts evaluation statistics."""

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.evaluation_stages: List[EvaluationStage] = []
        self.task_history: Dict[str, List[Tuple[int, bool, float]]] = defaultdict(list)

    def parse_logs(self) -> None:
        """Parse the training log file and extract all evaluation stages."""
        with open(self.log_path, 'r') as f:
            content = f.read()

        # Find all evaluation sections
        # Pattern to find evaluation start markers
        step_pattern = r'\[Step (\d+)\] Running.*evaluation.*\n\n=+\nEVALUATION: (\d+) tasks \(from (\d+) task types\)'

        # Find all evaluation blocks
        eval_matches = list(re.finditer(step_pattern, content))

        for i, match in enumerate(eval_matches):
            step = int(match.group(1))
            num_tasks = int(match.group(2))
            task_pool_size = int(match.group(3))

            # Determine the end of this evaluation block
            start_pos = match.end()
            if i + 1 < len(eval_matches):
                end_pos = eval_matches[i + 1].start()
            else:
                end_pos = len(content)

            eval_content = content[start_pos:end_pos]

            stage = EvaluationStage(
                step=step,
                num_tasks=num_tasks,
                task_pool_size=task_pool_size
            )

            # Parse individual task results
            self._parse_task_results(eval_content, stage)
            self.evaluation_stages.append(stage)

            # Update task history
            for result in stage.results:
                self.task_history[result.task_type].append(
                    (step, result.success, result.reward)
                )

    def _parse_task_results(self, content: str, stage: EvaluationStage) -> None:
        """Parse individual task results from an evaluation block."""
        # Pattern to match task blocks
        task_pattern = r'={80}\nTASK (\d+) \(Rollout #(\d+)\) - ID: ([a-f0-9]+)\nBenchmark: (\w+), Task: ([\w-]+)\n={80}\n\nGOAL: (.+?)\nInitial URL: (.+?)\n(.*?)(SUCCESS|FAILED) - Reward: ([\d.]+)\nTask length: (\d+) steps\nActions: (.+?)(?=\n\n={80}|\n\n=+\n\[|$)'

        for match in re.finditer(task_pattern, content, re.DOTALL):
            task_num = int(match.group(1))
            rollout_num = int(match.group(2))
            task_id = match.group(3)
            benchmark = match.group(4)
            task_type = match.group(5)
            goal = match.group(6).strip()
            initial_url = match.group(7).strip()
            pre_result = match.group(8)
            status = match.group(9)
            reward = float(match.group(10))
            task_length = int(match.group(11))
            actions_str = match.group(12).strip()

            # Parse actions
            actions = [a.strip() for a in actions_str.split(' -> ')]

            # Check for action errors
            has_action_error = 'Action error' in pre_result

            result = TaskResult(
                task_id=task_id,
                task_num=task_num,
                rollout_num=rollout_num,
                benchmark=benchmark,
                task_type=task_type,
                goal=goal,
                initial_url=initial_url,
                success=(status == 'SUCCESS'),
                reward=reward,
                task_length=task_length,
                actions=actions,
                has_action_error=has_action_error
            )
            stage.results.append(result)

    def get_summary_stats(self) -> Dict:
        """Get summary statistics across all evaluation stages."""
        stats = {
            'total_evaluations': len(self.evaluation_stages),
            'steps': [s.step for s in self.evaluation_stages],
            'success_rates': [s.success_rate for s in self.evaluation_stages],
            'avg_rewards': [s.avg_reward for s in self.evaluation_stages],
            'unique_task_types': len(self.task_history),
        }
        return stats

    def find_improved_tasks(self) -> Dict[str, Dict]:
        """Find tasks that failed in earlier steps but succeeded in later steps."""
        improved = {}

        for task_type, history in self.task_history.items():
            if not history:
                continue

            # Find first failure and first success after that failure
            first_failure_step = None
            first_success_after_failure = None

            for step, success, reward in history:
                if not success and first_failure_step is None:
                    first_failure_step = step
                elif success and first_failure_step is not None:
                    first_success_after_failure = step
                    break

            if first_failure_step is not None and first_success_after_failure is not None:
                # Calculate success rate progression
                success_by_step = defaultdict(list)
                for step, success, reward in history:
                    success_by_step[step].append(success)

                progression = []
                for step in sorted(success_by_step.keys()):
                    rate = sum(success_by_step[step]) / len(success_by_step[step])
                    progression.append((step, rate))

                improved[task_type] = {
                    'first_failure_step': first_failure_step,
                    'first_success_step': first_success_after_failure,
                    'improvement_steps': first_success_after_failure - first_failure_step,
                    'success_progression': progression,
                    'total_attempts': len(history),
                    'total_successes': sum(1 for _, s, _ in history if s),
                }

        return improved

    def find_regressed_tasks(self) -> Dict[str, Dict]:
        """Find tasks that succeeded earlier but failed later."""
        regressed = {}

        for task_type, history in self.task_history.items():
            if not history:
                continue

            first_success_step = None
            first_failure_after_success = None

            for step, success, reward in history:
                if success and first_success_step is None:
                    first_success_step = step
                elif not success and first_success_step is not None:
                    first_failure_after_success = step
                    break

            if first_success_step is not None and first_failure_after_success is not None:
                regressed[task_type] = {
                    'first_success_step': first_success_step,
                    'first_failure_step': first_failure_after_success,
                    'regression_at_step': first_failure_after_success,
                }

        return regressed

    def get_task_type_stats(self) -> Dict[str, Dict]:
        """Get detailed statistics per task type."""
        task_stats = {}

        for task_type, history in self.task_history.items():
            if not history:
                continue

            total = len(history)
            successes = sum(1 for _, s, _ in history if s)

            # Success rate by step
            by_step = defaultdict(lambda: {'success': 0, 'total': 0})
            for step, success, reward in history:
                by_step[step]['total'] += 1
                if success:
                    by_step[step]['success'] += 1

            step_rates = {
                step: data['success'] / data['total']
                for step, data in sorted(by_step.items())
            }

            task_stats[task_type] = {
                'total_attempts': total,
                'total_successes': successes,
                'overall_success_rate': successes / total if total > 0 else 0,
                'success_rate_by_step': step_rates,
                'first_seen_step': min(s for s, _, _ in history),
                'last_seen_step': max(s for s, _, _ in history),
            }

        return task_stats

    def get_noop_analysis(self) -> Dict:
        """Analyze tasks that result in all noop actions (model not responding)."""
        noop_stats = defaultdict(lambda: {'total': 0, 'all_noop': 0})

        for stage in self.evaluation_stages:
            for result in stage.results:
                noop_stats[result.task_type]['total'] += 1
                # Check if all actions are noop
                if all(a == 'noop()' for a in result.actions):
                    noop_stats[result.task_type]['all_noop'] += 1

        # Calculate noop rate
        noop_analysis = {}
        for task_type, stats in noop_stats.items():
            noop_analysis[task_type] = {
                'total_attempts': stats['total'],
                'all_noop_count': stats['all_noop'],
                'noop_rate': stats['all_noop'] / stats['total'] if stats['total'] > 0 else 0
            }

        return noop_analysis

    def print_report(self) -> None:
        """Print a comprehensive analysis report."""
        print("=" * 80)
        print("TRAINING LOG ANALYSIS REPORT")
        print("=" * 80)
        print(f"\nLog file: {self.log_path}")
        print(f"Total evaluation stages: {len(self.evaluation_stages)}")

        # Overall statistics
        print("\n" + "-" * 40)
        print("OVERALL STATISTICS")
        print("-" * 40)

        stats = self.get_summary_stats()
        print(f"Training steps analyzed: {stats['steps'][0]} to {stats['steps'][-1]}")
        print(f"Evaluation frequency: Every 5 steps")
        print(f"Unique task types seen: {stats['unique_task_types']}")

        # Success rate progression
        print("\n" + "-" * 40)
        print("SUCCESS RATE PROGRESSION")
        print("-" * 40)
        print(f"{'Step':<10} {'Success Rate':<15} {'Avg Reward':<15} {'Tasks'}")
        print("-" * 50)

        for stage in self.evaluation_stages:
            print(f"{stage.step:<10} {stage.success_rate*100:>6.1f}%{'':<8} {stage.avg_reward:>+.3f}{'':<8} {len(stage.results)}")

        # Best and worst stages
        best_stage = max(self.evaluation_stages, key=lambda s: s.success_rate)
        worst_stage = min(self.evaluation_stages, key=lambda s: s.success_rate)

        print(f"\nBest stage: Step {best_stage.step} ({best_stage.success_rate*100:.1f}% success)")
        print(f"Worst stage: Step {worst_stage.step} ({worst_stage.success_rate*100:.1f}% success)")

        # Improved tasks
        print("\n" + "-" * 40)
        print("IMPROVED TASKS (Failed -> Succeeded)")
        print("-" * 40)

        improved = self.find_improved_tasks()
        if improved:
            for task_type, info in sorted(improved.items(), key=lambda x: -x[1]['total_successes']):
                print(f"\n{task_type}:")
                print(f"  First failure at step: {info['first_failure_step']}")
                print(f"  First success at step: {info['first_success_step']}")
                print(f"  Total attempts: {info['total_attempts']}, Successes: {info['total_successes']}")

                # Show progression
                prog = info['success_progression']
                if len(prog) > 1:
                    prog_str = " -> ".join(f"Step {s}: {r*100:.0f}%" for s, r in prog)
                    print(f"  Progression: {prog_str}")
        else:
            print("No tasks showed improvement from failure to success.")

        # Regressed tasks
        print("\n" + "-" * 40)
        print("REGRESSED TASKS (Succeeded -> Failed)")
        print("-" * 40)

        regressed = self.find_regressed_tasks()
        if regressed:
            for task_type, info in sorted(regressed.items()):
                print(f"\n{task_type}:")
                print(f"  First success at step: {info['first_success_step']}")
                print(f"  First failure at step: {info['first_failure_step']}")
        else:
            print("No tasks showed regression from success to failure.")

        # NOOP analysis
        print("\n" + "-" * 40)
        print("NOOP ANALYSIS (Tasks with all noop actions)")
        print("-" * 40)

        noop_analysis = self.get_noop_analysis()
        high_noop = {k: v for k, v in noop_analysis.items() if v['noop_rate'] > 0.5}

        if high_noop:
            print("\nTasks with >50% all-noop rate:")
            for task_type, info in sorted(high_noop.items(), key=lambda x: -x[1]['noop_rate']):
                print(f"  {task_type}: {info['noop_rate']*100:.1f}% ({info['all_noop_count']}/{info['total_attempts']})")

        # Per-task statistics
        print("\n" + "-" * 40)
        print("PER-TASK TYPE STATISTICS")
        print("-" * 40)

        task_stats = self.get_task_type_stats()

        # Sort by overall success rate
        sorted_tasks = sorted(task_stats.items(), key=lambda x: -x[1]['overall_success_rate'])

        print(f"\n{'Task Type':<30} {'Success Rate':<15} {'Attempts':<10} {'Trend'}")
        print("-" * 70)

        for task_type, stats in sorted_tasks:
            rate = stats['overall_success_rate'] * 100
            attempts = stats['total_attempts']

            # Calculate trend
            step_rates = stats['success_rate_by_step']
            if len(step_rates) >= 2:
                steps = sorted(step_rates.keys())
                first_rate = step_rates[steps[0]]
                last_rate = step_rates[steps[-1]]
                if last_rate > first_rate + 0.1:
                    trend = "↑ Improving"
                elif last_rate < first_rate - 0.1:
                    trend = "↓ Declining"
                else:
                    trend = "→ Stable"
            else:
                trend = "-"

            print(f"{task_type:<30} {rate:>6.1f}%{'':<8} {attempts:<10} {trend}")

        print("\n" + "=" * 80)
        print("END OF REPORT")
        print("=" * 80)

    def export_to_json(self, output_path: str) -> None:
        """Export analysis results to JSON for further processing."""
        data = {
            'summary': self.get_summary_stats(),
            'evaluation_stages': [
                {
                    'step': s.step,
                    'num_tasks': s.num_tasks,
                    'success_rate': s.success_rate,
                    'avg_reward': s.avg_reward,
                    'results': [
                        {
                            'task_id': r.task_id,
                            'task_type': r.task_type,
                            'benchmark': r.benchmark,
                            'goal': r.goal,
                            'success': r.success,
                            'reward': r.reward,
                            'task_length': r.task_length,
                            'actions': r.actions,
                            'has_action_error': r.has_action_error
                        }
                        for r in s.results
                    ]
                }
                for s in self.evaluation_stages
            ],
            'improved_tasks': self.find_improved_tasks(),
            'regressed_tasks': self.find_regressed_tasks(),
            'task_type_stats': self.get_task_type_stats(),
            'noop_analysis': self.get_noop_analysis(),
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\nResults exported to: {output_path}")


    def get_learning_signal_analysis(self) -> Dict:
        """
        Analyze whether there's a real learning signal or just noise.

        Key metrics:
        1. Trend analysis (linear regression on success rates)
        2. Variance analysis (is variance decreasing over time?)
        3. Consistent improvers vs random fluctuation
        """
        import statistics

        stats = self.get_summary_stats()
        success_rates = stats['success_rates']
        steps = stats['steps']

        if len(success_rates) < 3:
            return {"error": "Not enough data points"}

        # 1. Linear trend (simple slope calculation)
        n = len(success_rates)
        mean_x = sum(steps) / n
        mean_y = sum(success_rates) / n

        numerator = sum((steps[i] - mean_x) * (success_rates[i] - mean_y) for i in range(n))
        denominator = sum((steps[i] - mean_x) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        # 2. Compare first half vs second half
        mid = n // 2
        first_half_avg = sum(success_rates[:mid]) / mid
        second_half_avg = sum(success_rates[mid:]) / (n - mid)

        # 3. Variance in first half vs second half
        first_half_var = statistics.variance(success_rates[:mid]) if mid > 1 else 0
        second_half_var = statistics.variance(success_rates[mid:]) if (n - mid) > 1 else 0

        # 4. Find consistently improving tasks (improved >= 2 times without regression)
        consistent_improvers = []
        for task_type, history in self.task_history.items():
            if len(history) < 4:
                continue

            # Group by step and get success rates
            by_step = defaultdict(list)
            for step, success, reward in history:
                by_step[step].append(success)

            step_rates = [(step, sum(successes)/len(successes))
                          for step, successes in sorted(by_step.items())]

            if len(step_rates) < 3:
                continue

            # Check for consistent improvement (later steps better than earlier)
            early_avg = sum(r for _, r in step_rates[:len(step_rates)//2]) / (len(step_rates)//2)
            late_avg = sum(r for _, r in step_rates[len(step_rates)//2:]) / (len(step_rates) - len(step_rates)//2)

            if late_avg > early_avg + 0.1:  # At least 10% improvement
                consistent_improvers.append({
                    'task': task_type,
                    'early_avg': early_avg,
                    'late_avg': late_avg,
                    'improvement': late_avg - early_avg,
                })

        # 5. Find tasks that are consistently failing (never improve)
        never_succeed = [task for task, history in self.task_history.items()
                         if all(not success for _, success, _ in history) and len(history) >= 3]

        return {
            'trend_slope': slope,  # Positive = improving
            'trend_per_100_steps': slope * 100,  # Expected improvement per 100 steps
            'first_half_avg': first_half_avg,
            'second_half_avg': second_half_avg,
            'improvement_first_to_second_half': second_half_avg - first_half_avg,
            'first_half_variance': first_half_var,
            'second_half_variance': second_half_var,
            'variance_change': second_half_var - first_half_var,  # Negative = more stable
            'consistent_improvers': sorted(consistent_improvers, key=lambda x: -x['improvement']),
            'never_succeed_tasks': never_succeed,
            'baseline_success_rate': success_rates[0],
            'final_success_rate': success_rates[-1],
            'peak_success_rate': max(success_rates),
            'peak_step': steps[success_rates.index(max(success_rates))],
        }

    def print_learning_analysis(self) -> None:
        """Print detailed analysis of whether learning is happening."""
        analysis = self.get_learning_signal_analysis()

        print("\n" + "=" * 80)
        print("LEARNING SIGNAL ANALYSIS")
        print("=" * 80)

        print("\n" + "-" * 40)
        print("1. OVERALL TREND")
        print("-" * 40)

        slope = analysis['trend_slope']
        if slope > 0.001:
            trend_str = f"↑ IMPROVING (+{analysis['trend_per_100_steps']:.1f}% per 100 steps)"
        elif slope < -0.001:
            trend_str = f"↓ DECLINING ({analysis['trend_per_100_steps']:.1f}% per 100 steps)"
        else:
            trend_str = "→ FLAT (no clear trend)"

        print(f"Trend: {trend_str}")
        print(f"Baseline (step 0): {analysis['baseline_success_rate']*100:.1f}%")
        print(f"Final: {analysis['final_success_rate']*100:.1f}%")
        print(f"Peak: {analysis['peak_success_rate']*100:.1f}% at step {analysis['peak_step']}")

        print("\n" + "-" * 40)
        print("2. FIRST HALF vs SECOND HALF")
        print("-" * 40)

        improvement = analysis['improvement_first_to_second_half']
        print(f"First half avg:  {analysis['first_half_avg']*100:.1f}%")
        print(f"Second half avg: {analysis['second_half_avg']*100:.1f}%")
        print(f"Change: {improvement*100:+.1f}%")

        if improvement > 0.05:
            print("→ Policy appears to be LEARNING (second half better)")
        elif improvement < -0.05:
            print("→ Policy may be DEGRADING (second half worse)")
        else:
            print("→ No significant change between halves")

        print("\n" + "-" * 40)
        print("3. STABILITY ANALYSIS")
        print("-" * 40)

        var_change = analysis['variance_change']
        print(f"First half variance:  {analysis['first_half_variance']:.4f}")
        print(f"Second half variance: {analysis['second_half_variance']:.4f}")

        if var_change < -0.01:
            print("→ Variance DECREASING (policy becoming more stable)")
        elif var_change > 0.01:
            print("→ Variance INCREASING (policy becoming less stable)")
        else:
            print("→ Variance stable")

        print("\n" + "-" * 40)
        print("4. CONSISTENTLY IMPROVING TASKS")
        print("-" * 40)

        improvers = analysis['consistent_improvers']
        if improvers:
            print(f"Found {len(improvers)} tasks with consistent improvement:\n")
            for item in improvers[:10]:  # Top 10
                print(f"  {item['task']}: {item['early_avg']*100:.0f}% → {item['late_avg']*100:.0f}% (+{item['improvement']*100:.0f}%)")
        else:
            print("No tasks showed consistent improvement across training.")

        print("\n" + "-" * 40)
        print("5. NEVER-SUCCEED TASKS (potential issues)")
        print("-" * 40)

        never_succeed = analysis['never_succeed_tasks']
        if never_succeed:
            print(f"Found {len(never_succeed)} tasks that NEVER succeeded:\n")
            for task in sorted(never_succeed)[:15]:
                print(f"  - {task}")
            if len(never_succeed) > 15:
                print(f"  ... and {len(never_succeed) - 15} more")
        else:
            print("All tasks succeeded at least once!")

        # Final verdict
        print("\n" + "=" * 80)
        print("VERDICT")
        print("=" * 80)

        # Scoring
        score = 0
        reasons = []

        if improvement > 0.05:
            score += 2
            reasons.append("+ Second half better than first half")
        elif improvement < -0.05:
            score -= 2
            reasons.append("- Second half worse than first half")

        if slope > 0.001:
            score += 1
            reasons.append("+ Positive trend slope")
        elif slope < -0.001:
            score -= 1
            reasons.append("- Negative trend slope")

        if len(improvers) >= 5:
            score += 2
            reasons.append(f"+ {len(improvers)} tasks consistently improving")
        elif len(improvers) >= 2:
            score += 1
            reasons.append(f"+ {len(improvers)} tasks consistently improving")

        if var_change < -0.01:
            score += 1
            reasons.append("+ Variance decreasing (more stable)")

        if len(never_succeed) > 30:
            score -= 1
            reasons.append(f"- {len(never_succeed)} tasks never succeed")

        for reason in reasons:
            print(f"  {reason}")

        print("")
        if score >= 3:
            print("📈 LEARNING SIGNAL DETECTED - Policy appears to be improving")
        elif score >= 1:
            print("📊 WEAK LEARNING SIGNAL - Some improvement but high variance")
        elif score >= -1:
            print("❓ INCONCLUSIVE - Cannot determine if learning is occurring")
        else:
            print("📉 NO LEARNING SIGNAL - Policy may not be improving")

        print("\n⚠️  NOTE: Evaluation uses temperature=0.7 (probabilistic sampling)")
        print("   For reliable assessment, use deterministic evaluation (temperature=0)")
        print("=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Analyze GRPO Web Agent training logs')
    parser.add_argument('--log-path', type=str,
                        default='/scratch/czr/env-gen/logs/training.logs',
                        help='Path to the training log file')
    parser.add_argument('--export-json', type=str, default=None,
                        help='Export results to JSON file')
    parser.add_argument('--quiet', action='store_true',
                        help='Only show summary, not full report')
    parser.add_argument('--learning-analysis', action='store_true',
                        help='Show detailed learning signal analysis')

    args = parser.parse_args()

    analyzer = TrainingLogAnalyzer(args.log_path)

    print(f"Parsing log file: {args.log_path}")
    analyzer.parse_logs()
    print(f"Found {len(analyzer.evaluation_stages)} evaluation stages")

    if args.learning_analysis:
        analyzer.print_learning_analysis()
    elif not args.quiet:
        analyzer.print_report()
    else:
        stats = analyzer.get_summary_stats()
        print(f"\nQuick Summary:")
        print(f"  Steps: {stats['steps'][0]} to {stats['steps'][-1]}")
        print(f"  Success rates: {[f'{r*100:.1f}%' for r in stats['success_rates']]}")

        improved = analyzer.find_improved_tasks()
        print(f"  Improved tasks: {len(improved)}")

    if args.export_json:
        analyzer.export_to_json(args.export_json)


if __name__ == '__main__':
    main()

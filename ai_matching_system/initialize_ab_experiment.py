"""
A/Bテスト実験の初期化スクリプト
評価改善の効果を測定するための実験を設定
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from ai_matching.utils.ab_testing import get_ab_testing_framework


def initialize_evaluation_experiment():
    """評価改善実験を初期化"""
    ab_testing = get_ab_testing_framework()
    
    # 実験1: セマンティック理解の効果測定
    experiment_id1 = ab_testing.create_experiment(
        name="semantic_understanding_v1",
        description="セマンティック理解による営業経験検出の改善効果を測定",
        control_config={
            "approach": "rule_based",
            "use_semantic_understanding": False,
            "strict_matching": True
        },
        variants=[
            {
                "name": "semantic_enabled",
                "approach": "semantic_heavy",
                "use_semantic_understanding": True,
                "strict_matching": False
            },
            {
                "name": "hybrid_approach",
                "approach": "hybrid",
                "use_semantic_understanding": True,
                "use_confidence_routing": True
            }
        ],
        traffic_allocation={
            "control": 0.33,
            "variant_a": 0.33,
            "variant_b": 0.34
        }
    )
    
    print(f"実験1を作成しました: ID={experiment_id1}")
    
    # 実験2: 評価プロンプトの改善効果測定
    experiment_id2 = ab_testing.create_experiment(
        name="evaluation_prompt_improvement_v1",
        description="改善された評価プロンプトの効果を測定",
        control_config={
            "prompt_version": "strict_v1",
            "allow_inference": False
        },
        variants=[
            {
                "name": "balanced_prompt",
                "prompt_version": "balanced_v2",
                "allow_inference": True,
                "inference_level": "moderate"
            }
        ]
    )
    
    print(f"実験2を作成しました: ID={experiment_id2}")
    
    # アクティブな実験を表示
    print("\n現在アクティブな実験:")
    for name, experiment in ab_testing.active_experiments.items():
        print(f"- {name}: {experiment['description']}")
        print(f"  開始日: {experiment['start_date']}")
        print(f"  トラフィック配分: {experiment['traffic_allocation']}")
    
    print("\n実験の初期化が完了しました！")
    print("環境変数 CURRENT_AB_EXPERIMENT を設定して実験を選択できます。")
    print("例: export CURRENT_AB_EXPERIMENT=semantic_understanding_v1")


if __name__ == "__main__":
    initialize_evaluation_experiment()
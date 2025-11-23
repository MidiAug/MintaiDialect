# -*- coding:utf-8 -*-
import json
import numpy as np
import torch
import os
from tqdm import tqdm


def compute_distance_matrix(data, metric="euclidean", device="cuda", block_size=512):
    """
    使用 PyTorch 计算 pairwise 距离矩阵，支持分块计算避免 OOM。
    Args:
        data (np.ndarray 或 torch.Tensor): 输入数据 (N, D)
        metric (str): 'euclidean' 或 'cosine'
        device (str): 计算设备 ('cuda' 或 'cpu')
        block_size (int): 分块大小，避免 OOM
    Returns:
        torch.Tensor: 距离矩阵 (N, N)
    """
    # 转成 torch tensor
    if not isinstance(data, torch.Tensor):
        data = torch.tensor(data, dtype=torch.float32)
    data = data.to(device)
    N, D = data.shape
    dist_matrix = torch.zeros((N, N), dtype=torch.float32, device=device)
    # 归一化（cosine 距离需要）
    if metric == "cosine":
        data_norm = torch.nn.functional.normalize(data, p=2, dim=1)
    else:
        data_norm = data
    # 分块计算
    for i in tqdm(range(0, N, block_size), desc="计算距离矩阵"):
        i_end = min(i + block_size, N)
        x = data_norm[i:i_end]  # 当前 block
        for j in range(0, N, block_size):
            j_end = min(j + block_size, N)
            y = data_norm[j:j_end]
            if metric == "euclidean":
                # (a - b)^2 = a^2 + b^2 - 2ab
                x2 = (x**2).sum(dim=1, keepdim=True)  # (block_i, 1)
                y2 = (y**2).sum(dim=1).unsqueeze(0)  # (1, block_j)
                dist = torch.sqrt(torch.clamp(x2 + y2 - 2 * x @ y.T, min=1e-12))
            elif metric == "cosine":
                sim = x @ y.T
                dist = 1 - sim
            else:
                raise ValueError(f"不支持的距离度量: {metric}")
            dist_matrix[i:i_end, j:j_end] = dist
    # 保证对称
    # dist_matrix = (dist_matrix + dist_matrix.T) / 2
    return dist_matrix.cpu().numpy()


def find_medoid_condition(
        condition_files: list[str],
        distance_metric: str = 'euclidean'
) -> dict:
        """
        找出condition latent分布中心的样本（medoid）

        Args:
            condition_files: condition文件路径列表
            distance_metric: 距离度量方式

        Returns:
            medoid信息字典
        """
        print(f"开始计算medoid，共{len(condition_files)}个样本")

        # 读取所有condition latent
        conditions = []
        condition_infos = []

        for condition_path in condition_files:
            if not os.path.exists(condition_path):
                print(f"Condition文件不存在: {condition_path}，跳过")
                continue

            try:
                cond = np.load(condition_path)
                conditions.append(cond)
                condition_infos.append({
                    'index': len(conditions) - 1,
                    'condition_path': condition_path
                })
            except Exception as e:
                print(f"加载condition文件失败: {condition_path}, 错误: {e}")
                continue

        if len(conditions) == 0:
            raise RuntimeError('没有找到有效的condition文件')

        print(f"成功读取{len(conditions)}个condition latent")

        # 将所有condition堆叠成一个数组
        conditions_array = np.stack(conditions, axis=0)
        print(f"Conditions数组形状: {conditions_array.shape}")

        # 将数据展平以便计算距离
        N, H, W = conditions_array.shape
        data_flat = conditions_array.reshape(N, H * W)

        # 计算距离矩阵
        print("计算距离矩阵...")
        dist_matrix = compute_distance_matrix(data_flat, distance_metric)

        # 找出medoid
        print("寻找medoid...")
        dist_sums = np.sum(dist_matrix, axis=1)
        medoid_idx = np.argmin(dist_sums)
        medoid_info = condition_infos[medoid_idx]
        medoid_condition = conditions[medoid_idx]
        print(f"找到medoid: 索引{medoid_idx}")
        print(f"Medoid到所有样本的距离之和: {dist_sums[medoid_idx]:.6f}")
        # 计算统计信息
        stats = {
            'total_samples': len(conditions),
            'medoid_index': int(medoid_idx),
            'medoid_distance_sum': float(dist_sums[medoid_idx]),
            'distance_metric': distance_metric,
            'distance_stats': {
                'mean': float(np.mean(dist_sums)),
                'std': float(np.std(dist_sums)),
                'min': float(np.min(dist_sums)),
                'max': float(np.max(dist_sums))
            }
        }
        return {
            'medoid_info': medoid_info,
            'medoid_condition': medoid_condition,
            'statistics': stats,
            'distance_matrix': dist_matrix
        }

from tools.extract_codec import save_medoid_results
from tools.extract_codec import save_speaker_info
from tools.extract_codec import split_dataset
def process():
    audio_list = "/home/yyz/ckpts/runs/mny-xm.txt"
    output_dir = "/data01/yyz/datas/mny-xm/mny-xm_20250928_200651"
    metadata_file = "/data01/yyz/datas/mny-xm/mny-xm_20250928_200651/metadata.jsonl"
    distance_metric = "euclidean"
    # condition_files = []
    # with open(metadata_file, encoding="utf-8") as sf:
    #     for line in sf:
    #         item = json.loads(line)
    #         condition_files.append(item["condition"])
    # medoid_result = find_medoid_condition(condition_files, distance_metric)
    # save_medoid_results(medoid_result, output_dir)
    # 分割数据集
    split_dataset(metadata_file, output_dir, train_ratio=0.99)
    # # 保存说话人信息
    # with open(metadata_file, 'r', encoding='utf-8') as f:
    #     lines = f.readlines()
    # save_speaker_info(audio_list, output_dir, lines)
    pass


if __name__ == '__main__':
    process()






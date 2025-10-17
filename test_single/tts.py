import requests
import os
import time
import shutil

# =============================
#           配置区域
# =============================

# 1. 配置你的TTS服务地址
#    - 如果服务和脚本在同一台机器上运行，使用 http://127.0.0.1:9002/tts
#    - 如果服务部署在另一台服务器上，请将其 IP 地址替换 127.0.0.1
TTS_API_URL = "http://127.0.0.1:9002/tts"

# 2. 指定存放输出WAV文件的目录
OUTPUT_DIR = "tts_output"

# 3. 输入你想要转换成语音的字符串列表
TEXTS_TO_SYNTHESIZE = [
    "Lî-sī'm-sī-ēîng-cuiciáo-zít'e.",    
    "Góa-Tân-Kah-kiⁿ-chhim-chai-kok-ka-beh-kiông-siāng",
    "Góa Tân Kah kiⁿ chhim chai kok ka beh kiông siāng",
    "Góa Tân-Kah-kiⁿ chhim chai kok-ka beh kiông-siāng",
]

# =============================
#          主程序逻辑
# =============================

def synthesize_text(text: str, output_path: str, speaking_rate: float = 1.0):
    """
    调用TTS API并保存音频文件。

    :param text: 要合成的文本。
    :param output_path: 音频文件的保存路径。
    :param speaking_rate: 语速，1.0为正常语速。
    """
    print(f"[*] 正在请求合成文本: '{text[:40]}...'")

    # 构造请求的JSON数据
    payload = {
        "text": text,
        "speaking_rate": speaking_rate
    }

    try:
        t0 = time.time()
        # 发送POST请求
        response = requests.post(TTS_API_URL, json=payload, timeout=60) # 设置60秒超时
        t1 = time.time()

        # 检查响应状态码
        if response.status_code == 200:
            # 将响应内容（即WAV文件的二进制数据）写入文件
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"[✓] 成功！音频已保存至: {output_path} (耗时: {t1 - t0:.2f}秒)")
            return True
        else:
            # 如果服务器返回错误
            print(f"[!] 错误！服务器返回状态码: {response.status_code}")
            print(f"    错误信息: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        # 如果请求过程中发生网络错误
        print(f"[!] 请求失败！无法连接到TTS服务: {e}")
        return False



def main():
    """
    主函数，处理所有文本的合成。
    """
    # 如果输出目录已存在，先清空再创建
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)  # 删除整个目录及内容
        print(f"[*] 已清空输出目录: {OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR)

    print("-" * 50)
    print(f"开始批量处理 {len(TEXTS_TO_SYNTHESIZE)} 条文本...")
    print("-" * 50)

    success_count = 0
    for i, text in enumerate(TEXTS_TO_SYNTHESIZE):
        output_filename = f"output_{i + 1}.wav"
        output_filepath = os.path.join(OUTPUT_DIR, output_filename)

        rate = 1.2 if i == 2 else 1.0

        if synthesize_text(text, output_filepath, speaking_rate=rate):
            success_count += 1
        
        print("-" * 20)

    print("\n" + "=" * 50)
    print(f"所有任务完成！成功: {success_count}, 失败: {len(TEXTS_TO_SYNTHESIZE) - success_count}")
    print(f"所有音频文件已保存到 '{os.path.abspath(OUTPUT_DIR)}' 目录中。")
    print("=" * 50)


if __name__ == "__main__":
    main()
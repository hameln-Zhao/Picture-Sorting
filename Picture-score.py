import streamlit as st
import os
import json
import random
from datetime import datetime

# ---------------------
# 1. 基本配置
# ---------------------
BASE_DIR = ".\\test1"  # 修改为你的实际路径
CATEGORIES = ["flux", "sdxl", "sd3", "sd1.5"]
TOTAL_ROUNDS = 10  # 固定10轮

# ---------------------
# 2. 读取/初始化 JSON（中间结果保存在一个固定文件中）
# ---------------------
RESULTS_FILE = "ranking_results.json"
if os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        try:
            results = json.load(f)
            if not isinstance(results, dict) or "rounds" not in results:
                results = {"rounds": [], "final_scores": {}}
        except json.JSONDecodeError:
            results = {"rounds": [], "final_scores": {}}
else:
    results = {"rounds": [], "final_scores": {}}


# ---------------------
# 3. 分组文件夹函数
# ---------------------
def get_grouped_folders():
    """将 BASE_DIR 下的 flux_1、sdxl_1 等文件夹按数字后缀分组。"""
    grouped_folders = {i: {} for i in range(1, TOTAL_ROUNDS + 1)}
    all_folders = [f for f in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, f))]
    for folder in all_folders:
        for category in CATEGORIES:
            if folder.startswith(category + "_"):
                parts = folder.split("_")
                if len(parts) > 1 and parts[-1].isdigit():
                    group_num = int(parts[-1])
                    if group_num in grouped_folders:
                        grouped_folders[group_num][category] = folder
    return grouped_folders


def get_images_for_round(round_num, grouped_folders):
    """
    从 grouped_folders 中获取当前轮次 round_num 对应的四个文件夹，
    各取第一张图片，返回一个 {category: image_path} 字典，
    并随机打乱顺序后返回。
    """
    selected_folders = grouped_folders.get(round_num, {})
    selected_images = {}
    for category, folder in selected_folders.items():
        folder_path = os.path.join(BASE_DIR, folder)
        imgs = [img for img in os.listdir(folder_path) if img.lower().endswith((".png", ".jpg", ".jpeg"))]
        if imgs:
            selected_images[category] = os.path.join(folder_path, imgs[0])
    items = list(selected_images.items())
    random.shuffle(items)
    return dict(items)


# ---------------------
# 4. 初始化会话状态
# ---------------------
if "round" not in st.session_state:
    st.session_state.round = 1
if "grouped_folders" not in st.session_state:
    st.session_state.grouped_folders = get_grouped_folders()
if "selected_images" not in st.session_state:
    st.session_state.selected_images = get_images_for_round(st.session_state.round, st.session_state.grouped_folders)
if "rankings" not in st.session_state:
    st.session_state.rankings = []
# 用于存储当前轮点击图片的顺序，列表中存储图片路径
if "clicked_order" not in st.session_state:
    st.session_state.clicked_order = []

# ---------------------
# 5. 用户引导说明（侧边栏）
# ---------------------
st.sidebar.title("用户引导")
st.sidebar.markdown(
    """
    **操作说明：**

    1. 页面会依次显示 4 张图片（来自不同类别）。点击图片下方的“选择”按钮确定排序顺序，
       最先点击的图片获得排序 1，最后点击的获得排序 4。
    2. 点击图片后，该图片会显示已获得的排序编号，且按钮将变为不可点击。
    3. 若想重新选择当前轮的排序，可点击“重置”按钮，清空本轮的排序记录。
    4. 当所有图片都已选择且排序顺序确定（4 张排序各不相同）后，“Next”按钮可用。
    5. 完成 10 轮评估后，页面将仅显示“评估已完成！谢谢使用。”。
    """
)

# ---------------------
# 6. 判断评估是否完成
# ---------------------
if st.session_state.round > TOTAL_ROUNDS:
    st.title("AI 生成图片排序评估")
    st.write("评估已完成！谢谢使用。")
    st.stop()

# ---------------------
# 7. 页面标题和当前轮次显示
# ---------------------
st.title("AI 生成图片排序评估")
st.write(f"**当前轮次：{st.session_state.round} / {TOTAL_ROUNDS}**")

# ---------------------
# 8. 显示图片及点击排序
# ---------------------
images = list(st.session_state.selected_images.values())
cols = st.columns(4)

for i, img in enumerate(images):
    with cols[i]:
        st.image(img, use_column_width=True)
        if img in st.session_state.clicked_order:
            rank = st.session_state.clicked_order.index(img) + 1
            st.write(f"已选排序：{rank}")
        else:
            if st.button("选择", key=f"btn_{st.session_state.round}_{i}"):
                if img not in st.session_state.clicked_order:
                    st.session_state.clicked_order.append(img)
                st.rerun()

# ---------------------
# 9. 重置按钮：清空当前轮点击记录
# ---------------------
if st.button("重置"):
    st.session_state.clicked_order = []
    st.rerun()

# ---------------------
# 10. 检查是否已完成本轮排序（必须4个且各不重复）
# ---------------------
next_disabled = False
if len(st.session_state.clicked_order) < 4:
    st.error("请点击所有图片以确定排序顺序！")
    next_disabled = True
elif len(set(st.session_state.clicked_order)) < 4:
    st.error("排序中存在重复，请重置后重新选择！")
    next_disabled = True

# ---------------------
# 11. Next 按钮处理
# ---------------------
if st.button("Next", disabled=next_disabled):
    # 构造排序字典：图片获得的排序为点击顺序（1~4）
    ranking = {img: st.session_state.clicked_order.index(img) + 1 for img in st.session_state.clicked_order}
    st.session_state.rankings.append(ranking)
    results["rounds"].append({"round": st.session_state.round, "ranking": ranking})
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    # 清空当前轮点击记录
    st.session_state.clicked_order = []
    st.session_state.round += 1
    if st.session_state.round <= TOTAL_ROUNDS:
        st.session_state.selected_images = get_images_for_round(st.session_state.round,
                                                                st.session_state.grouped_folders)
        st.rerun()
    else:
        # 完成所有轮次后，计算最终得分并生成带时间戳的最终 JSON 文件
        st.session_state.round = TOTAL_ROUNDS + 1
        final_scores = {cat: 0 for cat in CATEGORIES}
        for ranking in st.session_state.rankings:
            for img, rank in ranking.items():
                folder_name = os.path.basename(os.path.dirname(img))
                # 从文件夹名称（例如 flux_1）中取出类别名称（flux）
                category = folder_name.split("_")[0]
                final_scores[category] += (5 - rank)
        results["final_scores"] = final_scores
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"ranking_results_{timestamp}.json"
        with open(final_filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        st.write("评估已完成！谢谢使用。")
        st.stop()

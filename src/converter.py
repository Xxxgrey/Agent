import os
import gc
import logging
from pathlib import Path
import fitz  # PyMuPDF
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

# ====================== 限制多线程防段错误 ==========================
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# ====================== 日志配置 ==========================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ====================== 路径配置 ==========================
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / 'input'
OUTPUT_DIR = BASE_DIR / 'markdown'
IMAGE_DIR = OUTPUT_DIR / 'images'
OUTPUT_DIR.mkdir(exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# ====================== 提取 PDF 图片 ==========================
def extract_images_from_pdf(pdf_path, image_dir):
    logging.info(f"📥 提取图片：{pdf_path.name}")
    saved_images = []
    with fitz.open(pdf_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]
                image_name = f"{pdf_path.stem}_p{page_number}_{img_index}.{ext}"
                image_path = image_dir / image_name
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                saved_images.append(image_name)
    logging.info(f"🖼️ 共提取图片数：{len(saved_images)}")
    return saved_images

# ====================== 插入图片 Markdown 引用 ==========================
def insert_images_to_md(md_path, image_names):
    with open(md_path, 'a', encoding='utf-8') as f:
        for image_name in image_names:
            f.write(f'\n\n![Image](images/{image_name})\n')

# ====================== Marker 转换 PDF -> Markdown ==========================
def convert_pdf_to_md_with_marker(pdf_path, md_path):
    logging.info(f"📄 Marker 转换中：{pdf_path.name}")
    converter = None
    rendered = None
    text = ""
    try:
        converter = PdfConverter(artifact_dict=create_model_dict())  # ⚠️ 无 use_llm 参数
        rendered = converter(str(pdf_path))
        text, _, _ = text_from_rendered(rendered)

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(text)
    except Exception as e:
        logging.error(f"❌ Marker 转换失败: {e}")
    finally:
        # 清理资源（防止未定义错误）
        for var in [rendered, text, converter]:
            try:
                del var
            except:
                pass
        gc.collect()

# ====================== 主流程 ==========================
def process_pdf(pdf_path):
    logging.info(f"🚀 开始处理：{pdf_path.name}")
    md_filename = pdf_path.stem + '.md'
    md_path = OUTPUT_DIR / md_filename

    images = extract_images_from_pdf(pdf_path, IMAGE_DIR)
    convert_pdf_to_md_with_marker(pdf_path, md_path)
    if images:
        insert_images_to_md(md_path, images)

    logging.info(f"✅ 完成转换：{md_filename}")

# ====================== 程序入口 ==========================
if __name__ == '__main__':
    pdf_files = list(INPUT_DIR.glob('*.pdf'))
    if not pdf_files:
        logging.warning("⚠️ input 文件夹下没有 PDF 文件！")
    for pdf_file in pdf_files:
        process_pdf(pdf_file)
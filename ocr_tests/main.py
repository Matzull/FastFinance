from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_doc_orientation_classify=False, # Disables document orientation classification model via this parameter
    use_doc_unwarping=False, # Disables text image rectification model via this parameter
    use_textline_orientation=False, # Disables text line orientation classification model via this parameter
)
result = ocr.predict("./ocr_tests/img2.jpg")
for res in result:
    print(res.get("rec_texts"))

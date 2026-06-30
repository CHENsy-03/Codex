
import zipfile, xml.etree.ElementTree as ET
path = r"D:\edge下载\V4_Local_Industrial_Upgrade_Spec.docx"
text = ""
with zipfile.ZipFile(path) as z:
    xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for t in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
        if t.text: text += t.text
print(text)

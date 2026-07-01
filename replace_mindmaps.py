import sys, os
sys.path.insert(0, 'C:\\Users\\35594\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python')
from docx import Document

source_dir = 'D:\\企业微信\\文件储存\\WXWork\\1688854658857559\\Cache\\File\\2026-07'
out_dir = 'E:\\AI_Projects\\Codex\\output_images'

counties = ['威信县', '永善县', '昭阳区']

for county in counties:
    print(f'\n=== Processing {county} ===')
    src_path = os.path.join(source_dir, f'昭通市{county}_低空经济_架构思维导图版_更新版.docx')
    doc = Document(src_path)
    
    # Get list of image relationships
    rels = doc.part.rels
    image_rels = []
    for rel_id, rel in rels.items():
        if 'image' in rel.reltype:
            image_rels.append((rel_id, rel))
    
    print(f'  Found {len(image_rels)} images:')
    for rel_id, rel in image_rels:
        blob_size = len(rel.target_part.blob)
        print(f'    {rel_id}: {blob_size} bytes')
    
    # Replace the first 3 images with our new mind maps
    # We have 3 mind maps per county
    mindmap_files = sorted([f for f in os.listdir(out_dir) if county in f and 'mindmap' in f])
    print(f'  Found mindmaps: {mindmap_files}')
    
    for i, (rel_id, rel) in enumerate(image_rels):
        if i >= len(mindmap_files):
            break
        if i < 3:  # Replace first 3 images
            mindmap_path = os.path.join(out_dir, mindmap_files[i])
            if os.path.exists(mindmap_path):
                with open(mindmap_path, 'rb') as f:
                    new_blob = f.read()
                rel.target_part._blob = new_blob
                print(f'  Replaced {rel_id} with {mindmap_files[i]} ({len(new_blob)} bytes)')
    
    # Save
    doc.save(src_path)
    print(f'  Saved {county}')

print('\n=== Mind map replacement complete! ===')

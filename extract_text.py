import os
import subprocess
import concurrent.futures

image_dir = '/home/claudio/Imágenes/Fina Ergen Screen/'
output_file = '/home/claudio/Descargas/Fina-Ergen/.local_lab/docs/ocr_results.txt'

def extract_text(i):
    img_path = os.path.join(image_dir, f"{i}.png")
    if not os.path.exists(img_path):
        return f"Image {i}.png not found\n"
    
    try:
        # Run tesseract on the image, output to stdout
        result = subprocess.run(['tesseract', img_path, '-', '-l', 'spa+eng'], capture_output=True, text=True)
        text = result.stdout.strip()
        # if text is empty, return a placeholder
        if not text:
            text = "[NO TEXT FOUND]"
        return f"=== CAPTURA {i}.png ===\n{text}\n"
    except Exception as e:
        return f"=== CAPTURA {i}.png ===\nERROR: {str(e)}\n"

def main():
    print("Iniciando extracción de texto de 51 imágenes...")
    results = []
    # Usar ThreadPool para hacerlo más rápido
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(extract_text, i): i for i in range(1, 52)}
        # Sort by image number
        completed = []
        for future in concurrent.futures.as_completed(futures):
            num = futures[future]
            completed.append((num, future.result()))
        
        completed.sort(key=lambda x: x[0])
        for _, text in completed:
            results.append(text)
            
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(results))
    print(f"Resultados guardados en {output_file}")

if __name__ == "__main__":
    main()

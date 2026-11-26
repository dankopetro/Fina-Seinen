const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function generatePDF() {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    
    // Leer el archivo .md (que ya tiene estructura HTML)
    const filePath = '/home/claudio/Descargas/Fina-Seinen/.local_lab/docs/Manual_Usuario_v3.6.0.md';
    const htmlContent = fs.readFileSync(filePath, 'utf8');
    
    // Cargar el contenido
    await page.setContent(htmlContent, { waitUntil: 'networkidle0' });
    
    // Generar PDF
    const pdfPath = '/home/claudio/Descargas/Fina-Seinen/.local_lab/docs/Manual de Usuario completo Fina v3.6.0.pdf';
    await page.pdf({
        path: pdfPath,
        format: 'A4',
        printBackground: true,
        margin: { top: '20px', bottom: '20px', left: '20px', right: '20px' }
    });

    console.log(`PDF generado con éxito en: ${pdfPath}`);
    await browser.close();
}

generatePDF().catch(err => {
    console.error('Error generando PDF:', err);
    process.exit(1);
});

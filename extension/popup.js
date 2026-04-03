const OCR_SERVER_URL = "http://localhost:5000/solve";
const DISCLAIMER = "These master data details are for information purposes only and not to be relied upon for any legal or financial purpose. Any reliance leading to any losses is the sole responsibility of the decision-maker.";
const BRANDING = "Generated via tbhavar.in - Office of Tanmay Bhavar, CA.";

// --- 1. OCR Assistant Logic ---

document.getElementById('scrapeBtn').addEventListener('click', async () => {
    const cin = document.getElementById('cin').value.trim();
    const statusEl = document.getElementById('status');
    const captchaValueEl = document.getElementById('captchaValue');
    
    statusEl.innerText = "Searching for captcha...";
    captchaValueEl.innerText = "---";
    
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        // Step 1: Detect modal and get image
        const response = await chrome.tabs.sendMessage(tab.id, { action: "getModalState" });
        
        if (response && response.state === "captcha") {
            statusEl.innerText = "Captcha detected. Analyzing (4s)...";
            
            // Wait for 4 seconds as per bot-evasion requirement
            setTimeout(async () => {
                try {
                    statusEl.innerText = "Solving now...";
                    const ocrResponse = await fetch(OCR_SERVER_URL, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ image: response.image })
                    });
                    
                    const ocrResult = await ocrResponse.json();
                    
                    if (ocrResult.result && ocrResult.result.trim() !== "") {
                        captchaValueEl.innerText = ocrResult.result.trim();
                        statusEl.innerText = "Solved! Double-click to select.";
                        
                        // Copy to clipboard fallback
                        navigator.clipboard.writeText(ocrResult.result.trim()).catch(() => {
                            console.log("Clipboard auto-copy failed, but value is displayed.");
                        });
                        
                        // Also try to auto-fill (user manually clicks submit)
                        await chrome.tabs.sendMessage(tab.id, { 
                            action: "submitCaptcha", 
                            captcha: ocrResult.result.trim() 
                        });
                    } else {
                        statusEl.innerText = "OCR could not read characters. Try Refresing Captcha.";
                        captchaValueEl.innerText = "ERROR";
                    }
                } catch (fetchErr) {
                    statusEl.innerText = "OCR Server Offline (check terminal)";
                    console.error(fetchErr);
                }
            }, 4000);
        } else {
            statusEl.innerText = "No Captcha modal found on page.";
        }
    } catch (err) {
        statusEl.innerText = "Error: Please refresh the MCA page.";
        console.error(err);
    }
});

// --- 2. Excel to Branded HTML Logic ---

document.getElementById('convertBtn').addEventListener('click', () => {
    const fileInput = document.getElementById('excelFile');
    const statusEl = document.getElementById('excelStatus');
    
    if (!fileInput.files.length) {
        statusEl.innerText = "Please select a file first.";
        return;
    }
    
    const file = fileInput.files[0];
    const reader = new FileReader();
    
    statusEl.innerText = "Processing sheet data...";
    
    reader.onload = (e) => {
        try {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array' });
            
            const reportData = {
                master: {},
                charges: [],
                directors: []
            };
            
            // 1. Parse MasterData
            if (workbook.SheetNames.includes("MasterData")) {
                const sheet = workbook.Sheets["MasterData"];
                const json = XLSX.utils.sheet_to_json(sheet, { header: 1 });
                json.forEach(row => {
                    if (row.length >= 2 && row[0] && row[1]) {
                        reportData.master[row[0].toString().trim()] = row[1].toString().trim();
                    }
                });
            }
            
            // 2. Parse IndexOfCharges
            if (workbook.SheetNames.includes("IndexOfCharges")) {
                const json = XLSX.utils.sheet_to_json(workbook.Sheets["IndexOfCharges"]);
                if (json.length > 0 && !Object.values(json[0]).some(v => String(v).includes("No Records"))) {
                    reportData.charges = json;
                }
            }
            
            // 3. Parse Director Details
            if (workbook.SheetNames.includes("Director Details")) {
                reportData.directors = XLSX.utils.sheet_to_json(workbook.Sheets["Director Details"]);
            }
            
            if (Object.keys(reportData.master).length === 0) {
                throw new Error("Invalid MCA Excel format.");
            }
            
            statusEl.innerText = "Creating branded HTML...";
            generateBrandedReport(reportData);
            statusEl.innerText = "Complete! Check downloads.";
            
        } catch (err) {
            statusEl.innerText = "Error: " + err.message;
            console.error(err);
        }
    };
    
    reader.readAsArrayBuffer(file);
});

function generateBrandedReport(data) {
    const now = new Date().toLocaleString();
    const companyName = data.master["Company Name"] || "MCA_Report";
    const fileName = `${companyName.replace(/\s+/g, '_')}_TBHAVAR.html`;
    
    const masterRows = Object.entries(data.master)
        .map(([k, v]) => `<tr><td class="key">${k}</td><td class="val">${v}</td></tr>`)
        .join("");
        
    let chargesHtml = "";
    if (data.charges.length > 0) {
        const headers = Object.keys(data.charges[0]);
        chargesHtml = `
            <div class="table-header">INDEX OF CHARGES</div>
            <table>
                <thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead>
                <tbody>
                    ${data.charges.map(row => `<tr>${headers.map(h => `<td>${row[h] || '-'}</td>`).join("")}</tr>`).join("")}
                </tbody>
            </table>
        `;
    } else {
        chargesHtml = `<div class="table-header">INDEX OF CHARGES</div><p class="empty">No charges recorded.</p>`;
    }
    
    let directorsHtml = "";
    if (data.directors.length > 0) {
        const headers = Object.keys(data.directors[0]);
        directorsHtml = `
            <div class="table-header">DIRECTOR SIGNATORY DETAILS</div>
            <table>
                <thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead>
                <tbody>
                    ${data.directors.map(row => `<tr>${headers.map(h => `<td>${row[h] || '-'}</td>`).join("")}</tr>`).join("")}
                </tbody>
            </table>
        `;
    }

    const htmlContent = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&display=swap');
                body { font-family: 'Outfit', sans-serif; background: #fafafa; padding: 40px; color: #1a1a1a; line-height: 1.5; }
                .card { max-width: 900px; margin: auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); border: 1px solid #eee; }
                .header { border-bottom: 3px solid #d4af37; padding-bottom: 20px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .branding { font-size: 2rem; font-weight: 800; color: #d4af37; letter-spacing: 2px; }
                .date { font-size: 0.8rem; color: #777; font-weight: 600; }
                h1 { font-size: 1.4rem; text-align: center; margin-top: 0; color: #333; text-transform: uppercase; }
                .table-header { background: #1a1a1a; color: #d4af37; padding: 10px 15px; border-radius: 4px; font-weight: 700; margin-top: 30px; font-size: 14px; }
                table { width: 100%; border-collapse: collapse; margin-top: 10px; }
                th { background: #f9f9f9; text-align: left; padding: 12px; font-size: 11px; color: #666; border-bottom: 1px solid #ddd; }
                td { padding: 12px; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
                .key { font-weight: 700; color: #555; width: 40%; background: #fcfcfc; }
                .val { color: #000; font-weight: 400; }
                .empty { color: #999; font-style: italic; margin-top: 10px; font-size: 13px; }
                .footer { margin-top: 50px; border-top: 1px solid #eee; padding-top: 20px; font-size: 0.8rem; color: #888; }
                .disclaimer { font-size: 0.7rem; margin-top: 10px; opacity: 0.8; }
                @media print { body { padding: 0; } .card { box-shadow: none; border: none; } }
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <div class="branding">TBHAVAR.IN</div>
                    <div class="date">EXTRACTED: ${now}</div>
                </div>
                <h1>COMPANY MASTER DATA REPORT</h1>
                <p style="text-align: center; font-weight: 700; font-size: 1.2rem;">${companyName}</p>

                <div class="table-header">MASTER DATA DETAILS</div>
                <table>${masterRows}</table>

                ${chargesHtml}

                ${directorsHtml}

                <div class="footer">
                    <div style="color: #d4af37; font-weight: 700;">${BRANDING}</div>
                    <div class="disclaimer"><strong>DISCLAIMER:</strong> ${DISCLAIMER}</div>
                </div>
            </div>
        </body>
        </html>
    `;
    
    const blob = new Blob([htmlContent], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    chrome.downloads.download({ url: url, filename: fileName, saveAs: true });
}

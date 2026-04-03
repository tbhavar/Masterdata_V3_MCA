chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // --- Helper: Find element by text content ---
  const findByText = (selector, text) => {
    return [...document.querySelectorAll(selector)].find(el => el.innerText.includes(text));
  };

  if (request.action === "enterCIN") {
    const cinInput = [...document.querySelectorAll('input')].find(i => 
      (i.placeholder && i.placeholder.includes("Enter Company/LLP name")) || 
      i.id === "companyID"
    );
    
    if (!cinInput) {
      sendResponse({ error: "Could not find Search box." });
      return true;
    }
    
    cinInput.value = request.cin;
    cinInput.dispatchEvent(new Event('input', { bubbles: true }));
    
    // Fallback: Press Enter to trigger the modal if it didn't pop up automatically
    setTimeout(() => {
       const enterEvt = new KeyboardEvent('keydown', { keyCode: 13, bubbles: true });
       cinInput.dispatchEvent(enterEvt);
    }, 500);

    sendResponse({ success: true });
    return true;
  }

  if (request.action === "getModalState") {
    const modal = findByText("div", "Enter Captcha") || findByText("h4", "Captcha") || document.querySelector(".modal-content");
    
    if (modal && modal.offsetParent !== null) {
      const img = modal.querySelector("img") || document.querySelector("img[src*='captcha']");
      const canvas_el = modal.querySelector("canvas");

      if (img && img.src) {
        // If it's already a base64/data URL, send it directly
        if (img.src.startsWith("data:")) {
          sendResponse({ state: "captcha", image: img.src });
          return true;
        }

        // Wait for image to load natural dimensions
        if (img.naturalWidth > 0 && img.naturalHeight > 0) {
          const canvas = document.createElement("canvas");
          canvas.width = img.naturalWidth;
          canvas.height = img.naturalHeight;
          const ctx = canvas.getContext("2d");
          ctx.drawImage(img, 0, 0);
          sendResponse({ state: "captcha", image: canvas.toDataURL("image/png") });
          return true;
        }
      } else if (canvas_el) {
        // Handle canvas-based captchas
        sendResponse({ state: "captcha", image: canvas_el.toDataURL("image/png") });
        return true;
      }
    }

    // Check if Data Table is visible
    const table = document.querySelector(".master-data-table") || findByText("table", "Company Name");
    if (table) {
      sendResponse({ state: "results" });
      return true;
    }

    sendResponse({ state: "waiting" });
    return true;
  }

  if (request.action === "submitCaptcha") {
    console.log("Attempting to fill captcha:", request.captcha);
    const modal = findByText("div", "Enter Captcha") || document.querySelector(".modal-content") || document.body;
    
    // Find input: check for various common selectors and labels
    const input = modal.querySelector("input[type='text']") || 
                  modal.querySelector("input:not([type='hidden'])") ||
                  [...modal.querySelectorAll('input')].find(i => i.placeholder && i.placeholder.toLowerCase().includes("value"));

    if (input) {
      // Step 1: Click and Focus first (as suggested)
      input.click();
      input.focus();
      
      // Step 2: Wait 2 seconds before entering characters
      setTimeout(() => {
        input.select();
        try {
          // Try the most reliable "pasting" method used by browsers
          document.execCommand('insertText', false, request.captcha);
        } catch (e) {
          input.value = request.captcha;
        }
        
        ['input', 'change', 'blur'].forEach(evt => {
          input.dispatchEvent(new Event(evt, { bubbles: true }));
        });
        
        console.log("Captcha filled after 2s wait.");
        sendResponse({ success: true });
      }, 2000);
      
    } else {
      console.log("Could not find captcha input field.");
      sendResponse({ error: "Could not find captcha input field in the modal." });
    }
    return true;
  }

  if (request.action === "extractData") {
    const table = document.querySelector(".master-data-table") || findByText("table", "Company Name");
    if (table) {
      const rows = table.querySelectorAll("tr");
      const data = {};
      rows.forEach(row => {
        const cols = row.querySelectorAll("td");
        if (cols.length >= 2) {
          data[cols[0].innerText.trim()] = cols[1].innerText.trim();
        }
      });
      sendResponse({ data: data });
    } else {
      sendResponse({ error: "Data table not found." });
    }
    return true;
  }
});

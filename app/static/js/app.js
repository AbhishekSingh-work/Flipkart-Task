// ---  LOGISTICS VERIFICATION HUB LOGIC ---

document.addEventListener("DOMContentLoaded", () => {
    // --- Global State ---
    let activeTab = "validation";
    let webcamStream = null;
    let capturedBlob = null;
    let currentLookupProduct = null;
    const pollingIntervals = {};

    // --- DOM Elements ---
    const navItems = document.querySelectorAll(".nav-item");
    const sections = document.querySelectorAll(".page-section");
    const pageTitle = document.getElementById("page-title");
    const pageSubtitle = document.getElementById("page-subtitle");
    const displayOperator = document.getElementById("display-operator");
    
    // Ingestion Elements
    const dropzone = document.getElementById("upload-dropzone");
    const csvFileInput = document.getElementById("csv-file-input");
    const jobsList = document.getElementById("jobs-list");
    const noJobsPlaceholder = document.getElementById("no-jobs-placeholder");
    
    // Validation Elements
    const operatorNameInput = document.getElementById("operator_name");
    const widInput = document.getElementById("wid");
    const btnLookup = document.getElementById("btn-lookup");
    const videoWebcam = document.getElementById("webcam");
    const canvasCaptured = document.getElementById("captured-canvas");
    const imgPreview = document.getElementById("captured-preview");
    const cameraOverlay = document.getElementById("camera-overlay");
    const btnCapture = document.getElementById("btn-capture");
    const btnRetake = document.getElementById("btn-retake");
    const fileFallback = document.getElementById("file-fallback");
    const fileNameDisplay = document.getElementById("file-name-display");
    const btnSubmitVerification = document.getElementById("btn-submit-verification");
    const resultPlaceholder = document.getElementById("result-placeholder");
    const resultData = document.getElementById("result-data");
    const resWidTitle = document.getElementById("res-wid-title");
    const resExpiryBadge = document.getElementById("res-expiry-badge");
    const resEan = document.getElementById("res-ean");
    const resMfg = document.getElementById("res-mfg");
    const resExpiry = document.getElementById("res-expiry");
    const resDaysLeft = document.getElementById("res-days-left");
    const instructionEan = document.getElementById("instruction-ean");
    const instructionExpiry = document.getElementById("instruction-expiry");
    const actionAlert = document.getElementById("action-alert");
    
    // Reporting Elements
    const filterStartDate = document.getElementById("filter-start-date");
    const filterEndDate = document.getElementById("filter-end-date");
    const filterStatus = document.getElementById("filter-status");
    const btnRunReport = document.getElementById("btn-run-report");
    const btnExportCsv = document.getElementById("btn-export-csv");
    const tableBody = document.getElementById("report-table-body");
    
    // Stats Elements
    const statTotal = document.getElementById("stat-total");
    const statGood = document.getElementById("stat-good");
    const statWarning = document.getElementById("stat-warning");
    const statExpired = document.getElementById("stat-expired");
    const statMismatch = document.getElementById("stat-mismatch");
    
    // Modal Elements
    const imageModal = document.getElementById("image-modal");
    const modalImg = document.getElementById("modal-img");
    const modalClose = document.getElementById("modal-close");
    const modalTitleWid = document.getElementById("modal-title-wid");
    const modalTitleOperator = document.getElementById("modal-title-operator");

    // --- Tab Navigation Logic ---
    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const target = item.getAttribute("href").substring(1);
            switchTab(target);
        });
    });

    function switchTab(tabId) {
        activeTab = tabId;
        navItems.forEach(item => {
            if (item.getAttribute("href") === `#${tabId}`) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        sections.forEach(section => {
            if (section.getAttribute("id") === `sec-${tabId}`) {
                section.classList.add("active");
            } else {
                section.classList.remove("active");
            }
        });

        // Dynamic Header Updates
        if (tabId === "validation") {
            pageTitle.innerText = "Floor Product Validation";
            pageSubtitle.innerText = "Verify manufacturing and expiry details in real-time";
            startWebcam();
        } else {
            pageTitle.innerText = tabId === "ingestion" ? "Bulk Dataset Ingestion" : "Quality Assurance Reports";
            pageSubtitle.innerText = tabId === "ingestion" 
                ? "Process large inventory datasets via background task queues" 
                : "Auditing metrics, discrepancies tracking, and exports";
            stopWebcam();
        }

        if (tabId === "ingestion") {
            loadRecentJobs();
        }
        
        if (tabId === "reporting") {
            initReportDates();
        }
    }

    // --- Toast Notifications Helper ---
    function showToast(message, type = "info") {
        const container = document.getElementById("toast-container");
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        
        let iconClass = "fa-info-circle";
        if (type === "success") iconClass = "fa-check-circle";
        if (type === "warning") iconClass = "fa-exclamation-triangle";
        if (type === "error") iconClass = "fa-times-circle";
        
        toast.innerHTML = `
            <i class="fa-solid ${iconClass} toast-icon"></i>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        // Remove toast after animation completes
        setTimeout(() => {
            toast.style.animation = "toastSlide 0.3s reverse forwards";
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // --- Operator Name Caching (Usability) ---
    const cachedName = localStorage.getItem("operator_name");
    if (cachedName) {
        operatorNameInput.value = cachedName;
        displayOperator.innerText = cachedName;
    }

    operatorNameInput.addEventListener("input", (e) => {
        const name = e.target.value.trim();
        localStorage.setItem("operator_name", name);
        displayOperator.innerText = name || "Operator Mode";
    });

    // --- Webcam Capture Logic ---
    async function startWebcam() {
        if (webcamStream) return;
        try {
            const constraints = {
                video: {
                    facingMode: "environment", // Use back camera on mobiles
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                }
            };
            webcamStream = await navigator.mediaDevices.getUserMedia(constraints);
            videoWebcam.srcObject = webcamStream;
            videoWebcam.style.display = "block";
            imgPreview.style.display = "none";
            cameraOverlay.style.display = "flex";
        } catch (err) {
            console.warn("Camera access denied or unavailable: ", err);
            // Hide video, show prompt that camera is off and fallback is available
            videoWebcam.style.display = "none";
            cameraOverlay.style.display = "flex";
            cameraOverlay.querySelector(".scan-prompt").innerText = "Webcam offline. Use file upload fallback.";
        }
    }

    function stopWebcam() {
        if (webcamStream) {
            webcamStream.getTracks().forEach(track => track.stop());
            webcamStream = null;
        }
    }

    btnCapture.addEventListener("click", () => {
        if (!webcamStream) {
            showToast("Camera stream is not active. Use manual file upload.", "warning");
            return;
        }
        
        // Capture frame onto canvas
        canvasCaptured.width = videoWebcam.videoWidth;
        canvasCaptured.height = videoWebcam.videoHeight;
        const ctx = canvasCaptured.getContext("2d");
        ctx.drawImage(videoWebcam, 0, 0, canvasCaptured.width, canvasCaptured.height);
        
        // Convert to blob and preview
        canvasCaptured.toBlob((blob) => {
            capturedBlob = blob;
            const dataUrl = URL.createObjectURL(blob);
            imgPreview.src = dataUrl;
            imgPreview.style.display = "block";
            btnCapture.style.display = "none";
            btnRetake.style.display = "inline-flex";
            cameraOverlay.style.display = "none";
            fileNameDisplay.innerText = "Captured Snapshot Ready";
            checkSubmitValidationState();
        }, "image/jpeg", 0.85);
    });

    btnRetake.addEventListener("click", () => {
        capturedBlob = null;
        imgPreview.style.display = "none";
        btnRetake.style.display = "none";
        btnCapture.style.display = "inline-flex";
        cameraOverlay.style.display = "flex";
        fileNameDisplay.innerText = "";
        fileFallback.value = ""; // clear fallback file
        checkSubmitValidationState();
    });

    fileFallback.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (file) {
            capturedBlob = file;
            fileNameDisplay.innerText = `Selected: ${file.name}`;
            
            // Generate a preview
            const reader = new FileReader();
            reader.onload = (event) => {
                imgPreview.src = event.target.result;
                imgPreview.style.display = "block";
                cameraOverlay.style.display = "none";
                btnCapture.style.display = "none";
                btnRetake.style.display = "inline-flex";
                checkSubmitValidationState();
            };
            reader.readAsDataURL(file);
        }
    });

    // --- Product Lookup (WID Scan) ---
    async function performLookup() {
        const wid = widInput.value.trim();
        if (!wid) {
            showToast("Please enter a Warehouse ID.", "warning");
            return;
        }

        try {
            btnLookup.disabled = true;
            btnLookup.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            
            const response = await fetch(`/api/validation/product/${wid}`);
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Lookup failed.");
            }
            
            const product = await response.json();
            currentLookupProduct = product;
            
            // Populate Details Panel
            resWidTitle.innerText = `WID: ${product.wid}`;
            resEan.innerText = product.ean;
            resMfg.innerText = product.manufacturing_date || "Not Provided";
            resExpiry.innerText = product.expiry_date || "Not Provided";
            
            // Expiry countdown display
            if (product.days_to_expiry !== null) {
                const days = product.days_to_expiry;
                if (days < 0) {
                    resDaysLeft.innerText = `Lapsed by ${Math.abs(days)} days`;
                    resDaysLeft.className = "comp-value text-danger";
                } else {
                    resDaysLeft.innerText = `${days} days remaining`;
                    resDaysLeft.className = "comp-value highlight-text";
                }
            } else {
                resDaysLeft.innerText = "N/A";
                resDaysLeft.className = "comp-value text-muted";
            }
            
            // Badge logic
            resExpiryBadge.innerText = product.status_label;
            resExpiryBadge.className = "badge";
            if (product.status_label === "Expired") {
                resExpiryBadge.classList.add("badge-danger");
            } else if (product.status_label === "Expiring Soon") {
                resExpiryBadge.classList.add("badge-warning");
            } else if (product.status_label === "Good") {
                resExpiryBadge.classList.add("badge-good");
            } else {
                resExpiryBadge.classList.add("badge-purple");
            }
            
            // Instructions updates
            instructionEan.innerText = product.ean;
            instructionExpiry.innerText = product.expiry_date || "None";
            
            resultPlaceholder.style.display = "none";
            resultData.style.display = "block";
            
            showToast("Product record loaded.", "success");
            checkSubmitValidationState();
            
        } catch (err) {
            console.error(err);
            showToast(err.message, "error");
            resultData.style.display = "none";
            resultPlaceholder.style.display = "flex";
            currentLookupProduct = null;
            checkSubmitValidationState();
        } finally {
            btnLookup.disabled = false;
            btnLookup.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i>';
        }
    }

    btnLookup.addEventListener("click", performLookup);
    widInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            performLookup();
        }
    });

    function checkSubmitValidationState() {
        const hasOperator = operatorNameInput.value.trim().length > 0;
        const hasProduct = currentLookupProduct !== null;
        const hasPhoto = capturedBlob !== null;
        
        btnSubmitVerification.disabled = !(hasOperator && hasProduct && hasPhoto);
    }

    // Submit Validation Form
    const verificationForm = document.getElementById("verification-form");
    verificationForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const operator = operatorNameInput.value.trim();
        const wid = widInput.value.trim();
        
        if (!operator || !wid || !currentLookupProduct || !capturedBlob) {
            showToast("Form details are incomplete.", "error");
            return;
        }

        const formData = new FormData();
        formData.append("wid", wid);
        formData.append("operator_name", operator);
        formData.append("image", capturedBlob, "verification.jpg");

        try {
            btnSubmitVerification.disabled = true;
            btnSubmitVerification.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting...';
            
            const response = await fetch("/api/validation/verify", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Submission failed.");
            }

            const result = await response.json();
            showToast(`Verification Logged for WID ${result.wid}!`, "success");
            
            // Reset fields
            widInput.value = "";
            currentLookupProduct = null;
            capturedBlob = null;
            imgPreview.style.display = "none";
            btnRetake.style.display = "none";
            btnCapture.style.display = "inline-flex";
            cameraOverlay.style.display = "flex";
            fileNameDisplay.innerText = "";
            fileFallback.value = "";
            
            // Reset comparison view
            resultData.style.display = "none";
            resultPlaceholder.style.display = "flex";
            
            checkSubmitValidationState();
            
        } catch (err) {
            console.error(err);
            showToast(err.message, "error");
        } finally {
            btnSubmitVerification.innerHTML = '<i class="fa-solid fa-circle-check"></i> Submit Verification Log';
        }
    });


    // --- Bulk Ingestion Logic ---
    
    // Drag & Drop event bindings
    ["dragenter", "dragover"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
        }, false);
    });

    dropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleCsvUpload(files[0]);
        }
    });

    dropzone.addEventListener("click", () => {
        csvFileInput.click();
    });

    csvFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleCsvUpload(e.target.files[0]);
        }
    });

    async function handleCsvUpload(file) {
        if (!file.name.toLowerCase().endsWith(".csv")) {
            showToast("Please upload a valid CSV file.", "error");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
            showToast("Uploading dataset...", "info");
            const response = await fetch("/api/ingestion/upload", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Ingestion trigger failed.");
            }

            const job = await response.json();
            showToast("CSV Uploaded successfully! Processing started.", "success");
            
            addJobToUi(job);
            startJobPolling(job.job_id);
            
        } catch (err) {
            console.error(err);
            showToast(err.message, "error");
        }
    }

    function addJobToUi(job) {
        noJobsPlaceholder.style.display = "none";
        
        // Remove existing element if present
        const existing = document.getElementById(`job-item-${job.job_id}`);
        if (existing) existing.remove();

        const item = document.createElement("div");
        item.className = "job-item";
        item.id = `job-item-${job.job_id}`;
        
        const mfgTime = new Date(job.created_at).toLocaleTimeString();
        
        item.innerHTML = `
            <div class="job-item-header">
                <span class="job-title">Job: #${job.job_id.substring(0, 8)}</span>
                <span class="job-time">${mfgTime}</span>
            </div>
            <div class="job-progress-container">
                <div class="job-progress-text">
                    <span class="job-status-label" id="job-status-${job.job_id}">${job.status}</span>
                    <span class="job-pct" id="job-pct-${job.job_id}">${job.percent_complete}%</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill ${job.status}" id="job-bar-${job.job_id}" style="width: ${job.percent_complete}%"></div>
                </div>
            </div>
            <div class="job-row-details" id="job-rows-${job.job_id}" style="font-size: 11px; color: var(--color-text-muted);">
                Processed: ${job.processed_rows} / ${job.total_rows} records
            </div>
            <div class="job-error" id="job-error-${job.job_id}" style="display: ${job.error_message ? 'block' : 'none'};">
                ${job.error_message || ''}
            </div>
        `;
        
        jobsList.insertBefore(item, jobsList.firstChild);
    }

    function startJobPolling(jobId) {
        if (pollingIntervals[jobId]) return;
        
        pollingIntervals[jobId] = setInterval(async () => {
            try {
                const response = await fetch(`/api/ingestion/status/${jobId}`);
                if (!response.ok) return;
                
                const job = await response.json();
                updateJobUi(job);
                
                if (job.status === "COMPLETED") {
                    clearInterval(pollingIntervals[jobId]);
                    delete pollingIntervals[jobId];
                    showToast(`Dataset ingestion job #${jobId.substring(0, 8)} completed successfully!`, "success");
                } else if (job.status === "FAILED") {
                    clearInterval(pollingIntervals[jobId]);
                    delete pollingIntervals[jobId];
                    showToast(`Dataset job #${jobId.substring(0, 8)} failed.`, "error");
                }
            } catch (err) {
                console.error("Polling error: ", err);
            }
        }, 1500);
    }

    function updateJobUi(job) {
        const statusEl = document.getElementById(`job-status-${job.job_id}`);
        const pctEl = document.getElementById(`job-pct-${job.job_id}`);
        const barEl = document.getElementById(`job-bar-${job.job_id}`);
        const rowsEl = document.getElementById(`job-rows-${job.job_id}`);
        const errorEl = document.getElementById(`job-error-${job.job_id}`);
        
        if (statusEl) statusEl.innerText = job.status;
        if (pctEl) pctEl.innerText = `${job.percent_complete}%`;
        
        if (barEl) {
            barEl.style.width = `${job.percent_complete}%`;
            barEl.className = `progress-bar-fill ${job.status}`;
        }
        
        if (rowsEl) {
            rowsEl.innerText = `Processed: ${job.processed_rows} / ${job.total_rows} records`;
        }
        
        if (errorEl && job.error_message) {
            errorEl.innerText = job.error_message;
            errorEl.style.display = "block";
        }
    }

    async function loadRecentJobs() {
        try {
            const response = await fetch("/api/ingestion/recent");
            if (!response.ok) return;
            const jobs = await response.json();
            
            if (jobs.length === 0) {
                noJobsPlaceholder.style.display = "block";
                jobsList.innerHTML = "";
            } else {
                noJobsPlaceholder.style.display = "none";
                jobsList.innerHTML = "";
                jobs.forEach(job => {
                    addJobToUi(job);
                    if (job.status === "PENDING" || job.status === "PROCESSING") {
                        startJobPolling(job.job_id);
                    }
                });
            }
        } catch (err) {
            console.error(err);
        }
    }


    // --- Reporting & QA Logic ---
    let reportDataCache = [];

    function initReportDates() {
        // Default start date = 7 days ago, end date = today
        const today = new Date();
        const pastWeek = new Date();
        pastWeek.setDate(today.getDate() - 7);
        
        filterStartDate.value = pastWeek.toISOString().split('T')[0];
        filterEndDate.value = today.toISOString().split('T')[0];
    }

    async function runReportQuery() {
        const start = filterStartDate.value;
        const end = filterEndDate.value;
        
        if (!start || !end) {
            showToast("Both dates are required.", "warning");
            return;
        }

        try {
            btnRunReport.disabled = true;
            btnRunReport.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
            
            const response = await fetch(`/api/reporting/report?start_date=${start}&end_date=${end}`);
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Query failed.");
            }
            
            const report = await response.json();
            reportDataCache = report.activities;
            
            // Render Stats
            statTotal.innerText = report.summary.total_verifications;
            statGood.innerText = report.summary.good_count;
            statWarning.innerText = report.summary.expiring_soon_count;
            statExpired.innerText = report.summary.expired_count;
            statMismatch.innerText = report.summary.mismatch_count || 0;
            
            renderFilteredTable();
            showToast("Report loaded.", "success");
            
        } catch (err) {
            console.error(err);
            showToast(err.message, "error");
        } finally {
            btnRunReport.disabled = false;
            btnRunReport.innerHTML = '<i class="fa-solid fa-rotate"></i> Run Query';
        }
    }

    function renderFilteredTable() {
        const filterVal = filterStatus.value;
        
        // Filter rows client side if status is chosen
        let filtered = reportDataCache;
        if (filterVal !== "ALL") {
            if (filterVal === "Data Mismatch") {
                filtered = reportDataCache.filter(row => !row.ean || row.status_label === "Data Mismatch");
            } else {
                filtered = reportDataCache.filter(row => row.status_label === filterVal);
            }
        }
        
        tableBody.innerHTML = "";
        
        if (filtered.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="table-empty">
                        <i class="fa-solid fa-folder-open"></i>
                        <p>No verification activities match current filters.</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        filtered.forEach(row => {
            const tr = document.createElement("tr");
            
            // Format Timestamp: YYYY-MM-DD HH:MM
            const dateObj = new Date(row.timestamp);
            const dateStr = dateObj.toLocaleDateString();
            const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            // Format Badge
            let badgeClass = "badge-purple";
            if (row.status_label === "Good") badgeClass = "badge-good";
            else if (row.status_label === "Expiring Soon") badgeClass = "badge-warning";
            else if (row.status_label === "Expired") badgeClass = "badge-danger";
            else if (row.status_label === "Data Mismatch") badgeClass = "badge-danger";
            
            const badgeHtml = `<span class="badge ${badgeClass}">${row.status_label}</span>`;
            
            // Photo cell
            const photoHtml = row.image_path 
                ? `<img src="${row.image_path}" class="table-thumbnail" alt="thumbnail" data-wid="${row.wid}" data-operator="${row.operator_name}">`
                : `<span class="no-photo-badge">None</span>`;
                
            tr.innerHTML = `
                <td><strong>${dateStr}</strong> <span style="font-size:11px; color:var(--color-text-muted);">${timeStr}</span></td>
                <td><code style="font-size:12px; color:var(--color-primary);">${row.wid}</code></td>
                <td>${row.ean || '<span class="text-danger">Missing Record</span>'}</td>
                <td>${row.operator_name}</td>
                <td>${row.manufacturing_date || '-'}</td>
                <td>${row.expiry_date || '-'}</td>
                <td>${badgeHtml}</td>
                <td>${photoHtml}</td>
            `;
            
            tableBody.appendChild(tr);
        });
        
        // Add click events to thumbnails
        const thumbnails = tableBody.querySelectorAll(".table-thumbnail");
        thumbnails.forEach(thumb => {
            thumb.addEventListener("click", () => {
                const src = thumb.getAttribute("src");
                const wid = thumb.getAttribute("data-wid");
                const operator = thumb.getAttribute("data-operator");
                
                modalImg.src = src;
                modalTitleWid.innerText = `WID: ${wid}`;
                modalTitleOperator.innerText = `Checked by: ${operator}`;
                imageModal.style.display = "flex";
            });
        });
    }

    // Modal Close actions
    modalClose.addEventListener("click", () => imageModal.style.display = "none");
    imageModal.addEventListener("click", (e) => {
        if (e.target === imageModal) {
            imageModal.style.display = "none";
        }
    });

    btnRunReport.addEventListener("click", runReportQuery);
    filterStatus.addEventListener("change", renderFilteredTable);

    // --- Export CSV Logic (Local Javascript Generator) ---
    btnExportCsv.addEventListener("click", () => {
        if (reportDataCache.length === 0) {
            showToast("No data to export. Run a query first.", "warning");
            return;
        }

        const headers = ["Timestamp", "WID", "EAN", "Operator_Name", "Mfg_Date", "Expiry_Date", "Health_Status", "Image_URL"];
        
        const csvRows = [headers.join(",")];
        
        reportDataCache.forEach(row => {
            const values = [
                `"${row.timestamp}"`,
                `"${row.wid}"`,
                `"${row.ean || ''}"`,
                `"${row.operator_name.replace(/"/g, '""')}"`,
                `"${row.manufacturing_date || ''}"`,
                `"${row.expiry_date || ''}"`,
                `"${row.status_label}"`,
                `"${row.image_path || ''}"`
            ];
            csvRows.push(values.join(","));
        });
        
        const csvContent = "data:text/csv;charset=utf-8," + csvRows.join("\n");
        const encodedUri = encodeURI(csvContent);
        
        const link = document.createElement("a");
        const timestampStr = new Date().toISOString().substring(0, 10);
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `qa_report_${timestampStr}.csv`);
        document.body.appendChild(link);
        
        link.click();
        document.body.removeChild(link);
        
        showToast("QA report exported as CSV.", "success");
    });


    // --- Initialization ---
    // Start on floor validation tab
    switchTab("validation");
});

        // Auth Logic
        let isLoginMode = true;

        async function loadSettings() {
            try {
                const res = await fetch('/api/settings');
                if (res.status === 401) return;
                const data = await res.json();
                document.getElementById('settings-domain').value = data.base_domain || '';
                document.getElementById('settings-webhook').value = data.webhook_email || '';
                document.getElementById('settings-geo').value = data.default_geo || '';
            } catch (err) {
                console.error(err);
            }
        }

        async function saveSettings() {
            const data = {
                base_domain: document.getElementById('settings-domain').value,
                webhook_email: document.getElementById('settings-webhook').value,
                default_geo: document.getElementById('settings-geo').value
            };
            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (res.status === 401) { checkSession(); return; }
                const result = await res.json();
                if (result.success) {
                    alert(result.message);
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (err) {
                alert('API Error: ' + err);
            }
        }

        async function checkSession() {
            try {
                const res = await fetch('/api/session');
                const data = await res.json();
                if (data.logged_in) {
                    document.getElementById('auth-overlay').style.display = 'none';
                    loadSettings();
                    loadQRCodes();
                } else {
                    document.getElementById('auth-overlay').style.display = 'flex';
                }
            } catch (err) {
                console.error(err);
            }
        }

        function toggleAuthMode() {
            const card = document.querySelector('.auth-left-content');
            card.style.transform = 'scale(0.95)';
            card.style.opacity = '0.5';
            
            setTimeout(() => {
                isLoginMode = !isLoginMode;
                document.getElementById('auth-title').innerText = isLoginMode ? 'Login to your account!' : 'Create your account!';
                document.getElementById('auth-subtitle').innerText = isLoginMode ? 'Enter your registered email address and password to login!' : 'Sign up to get started with QR PRO.';
                document.getElementById('auth-btn').innerText = isLoginMode ? 'Login' : 'Sign Up';
                document.getElementById('auth-toggle-text').innerText = isLoginMode ? "Don't have an account?" : "Already have an account?";
                document.getElementById('auth-toggle-link').innerText = isLoginMode ? 'Create one' : 'Login';
                
                const confirmPwdGroup = document.getElementById('auth-confirm-group');
                const authOptions = document.getElementById('auth-options-group');
                if (!isLoginMode) {
                    confirmPwdGroup.style.display = 'block';
                    document.getElementById('auth-confirm-password').setAttribute('required', 'true');
                    authOptions.style.display = 'none';
                } else {
                    confirmPwdGroup.style.display = 'none';
                    document.getElementById('auth-confirm-password').removeAttribute('required');
                    authOptions.style.display = 'flex';
                }
                
                card.style.transform = 'scale(1)';
                card.style.opacity = '1';
            }, 200);
        }

        async function handleAuth(e) {
            e.preventDefault();
            const email = document.getElementById('auth-email').value;
            const password = document.getElementById('auth-password').value;
            
            if (!isLoginMode) {
                const confirmPassword = document.getElementById('auth-confirm-password').value;
                if (password !== confirmPassword) {
                    alert("Passwords do not match!");
                    return;
                }
            }
            
            const url = isLoginMode ? '/api/login' : '/api/register';
            const formData = new FormData();
            formData.append('email', email);
            formData.append('password', password);

            try {
                const res = await fetch(url, { method: 'POST', body: formData });
                const data = await res.json();
                if (data.success) {
                    checkSession();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (err) {
                alert('API Error: ' + err);
            }
        }

        async function handleLogout() {
            try {
                await fetch('/api/logout', { method: 'POST' });
                checkSession();
            } catch (err) {
                console.error(err);
            }
        }

        // Initialize App
        checkSession();

        let currentEditQrId = null;
        
        // Tab switching logic
        const titles = {
            'dashboard': { title: 'Dashboard', sub: 'Create and route dynamic QR codes.' },
            'security': { title: 'Security & Limits', sub: 'Protect your codes with passwords, expiry dates, and scan limits.' },
            'brand': { title: 'Brand & Logo', sub: 'Make your QR codes stand out with custom logos and colors.' },
            'settings': { title: 'Settings', sub: 'Configure domains and global rules.' }
        };

        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            event.target.classList.add('active');
            
            const titles = {
                'dashboard': {title: currentEditQrId ? 'Update QR Code' : 'Dashboard', sub: currentEditQrId ? `Editing QR ID: ${currentEditQrId}` : 'Create and route dynamic QR codes.'},
                'security': {title: 'Security', sub: 'Add passwords, limits, and expiries.'},
                'brand': {title: 'Brand', sub: 'Customize QR appearance.'},
                'manage': {title: 'Manage QR Codes', sub: 'View and edit existing QR codes.'},
                'settings': {title: 'Settings', sub: 'Application configuration.'}
            };
            
            document.getElementById('page-title').innerText = titles[tabId].title;
            document.getElementById('page-subtitle').innerText = titles[tabId].sub;

            if(tabId === 'manage') loadQRCodes();
        }

        // --- Custom JS Scrollbar Logic ---
        const scrollContainer = document.getElementById('scroll-container');
        const scrollbar = document.getElementById('custom-scrollbar');
        const thumb = document.getElementById('custom-thumb');
        let isDragging = false;
        let startY;
        let startScrollTop;

        function updateThumb() {
            const scrollRatio = scrollContainer.scrollTop / (scrollContainer.scrollHeight - scrollContainer.clientHeight);
            const thumbMaxTop = scrollbar.clientHeight - thumb.clientHeight;
            
            // Adjust thumb height based on content size
            let thumbHeight = (scrollContainer.clientHeight / scrollContainer.scrollHeight) * scrollbar.clientHeight;
            if(thumbHeight < 40) thumbHeight = 40;
            if(thumbHeight >= scrollbar.clientHeight) {
                scrollbar.style.display = 'none'; // hide if no scroll needed
            } else {
                scrollbar.style.display = 'block';
                thumb.style.height = thumbHeight + 'px';
                thumb.style.top = (scrollRatio * thumbMaxTop) + 'px';
            }
        }

        scrollContainer.addEventListener('scroll', updateThumb);
        window.addEventListener('resize', updateThumb);
        // Initial setup
        setTimeout(updateThumb, 100);

        // Drag logic
        thumb.addEventListener('mousedown', (e) => {
            isDragging = true;
            startY = e.clientY;
            startScrollTop = scrollContainer.scrollTop;
            document.body.style.userSelect = 'none'; // prevent text selection
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const deltaY = e.clientY - startY;
            const scrollRatio = deltaY / scrollbar.clientHeight;
            const scrollDelta = scrollRatio * scrollContainer.scrollHeight;
            scrollContainer.scrollTop = startScrollTop + scrollDelta;
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
            document.body.style.userSelect = 'auto';
        });

        // 3D Mouse Tilt Script
        const cards = document.querySelectorAll('.js-tilt-card');
        cards.forEach(card => {
            card.addEventListener('mousemove', e => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                
                const rotateX = ((y - centerY) / centerY) * -8;
                const rotateY = ((x - centerX) / centerX) * 8;
                
                card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
                card.style.background = `
                    linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01)),
                    radial-gradient(circle at ${x}px ${y}px, rgba(255,255,255,0.15) 0%, transparent 50%)
                `;
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
                card.style.background = `rgba(255, 255, 255, 0.03)`;
            });
        });

        // Show selected PDF filename
        document.getElementById('pdf-upload').addEventListener('change', function(e) {
            const display = document.getElementById('pdf-filename-display');
            if (this.files && this.files.length > 0) {
                display.innerText = "📄 Selected: " + this.files[0].name;
                display.style.display = 'block';
            } else {
                display.style.display = 'none';
            }
        });

        // Toggle PDF Upload & vCard visibility
        document.getElementById('qr-type').addEventListener('change', function(e) {
            const val = e.target.value;
            const contentData = document.getElementById('content-data');
            const pdfUpload = document.getElementById('pdf-upload');
            const pdfDisplay = document.getElementById('pdf-filename-display');
            const vcardBuilder = document.getElementById('vcard-builder');
            const contentLabel = document.getElementById('content-label');
            
            contentData.style.display = 'none';
            pdfUpload.style.display = 'none';
            pdfDisplay.style.display = 'none';
            vcardBuilder.style.display = 'none';

            if (val === 'pdf') {
                pdfUpload.style.display = 'block';
                if (pdfUpload.files && pdfUpload.files.length > 0) {
                    pdfDisplay.style.display = 'block';
                }
                contentLabel.innerText = 'Upload PDF Document';
            } else if (val === 'vcard') {
                vcardBuilder.style.display = 'block';
                contentLabel.innerText = 'Advanced vCard Builder';
            } else {
                contentData.style.display = 'block';
                contentLabel.innerText = 'Destination Data';
            }
        });

        // Backend Integration (API Calls)
        document.getElementById('btn-generate').addEventListener('click', async () => {
            const formData = new FormData();
            
            // Basic
            const qrType = document.getElementById('qr-type').value;
            formData.append('type', qrType);
            
            if (qrType === 'pdf') {
                const pdfFile = document.getElementById('pdf-upload').files[0];
                if (pdfFile) formData.append('pdf_file', pdfFile);
            } else if (qrType === 'vcard') {
                // Collect all vcard data
                const vcardData = {
                    fn: document.getElementById('vc-fn').value,
                    ln: document.getElementById('vc-ln').value,
                    prefix: document.getElementById('vc-prefix').value,
                    suffix: document.getElementById('vc-suffix').value,
                    photo: document.getElementById('vc-photo').value,
                    company: document.getElementById('vc-company').value,
                    title: document.getElementById('vc-title').value,
                    dept: document.getElementById('vc-dept').value,
                    role: document.getElementById('vc-role').value,
                    mobile: document.getElementById('vc-mobile').value,
                    work: document.getElementById('vc-work').value,
                    email: document.getElementById('vc-email').value,
                    website: document.getElementById('vc-website').value,
                    linkedin: document.getElementById('vc-linkedin').value,
                    github: document.getElementById('vc-github').value,
                    whatsapp: document.getElementById('vc-whatsapp').value,
                    street: document.getElementById('vc-street').value,
                    city: document.getElementById('vc-city').value,
                    state: document.getElementById('vc-state').value,
                    zip: document.getElementById('vc-zip').value,
                    country: document.getElementById('vc-country').value,
                    bday: document.getElementById('vc-bday').value,
                    notes: document.getElementById('vc-notes').value,
                    uid: document.getElementById('vc-uid').value,
                    rev: document.getElementById('vc-rev').value,
                    kind: document.getElementById('vc-kind').value,
                    geo: document.getElementById('vc-geo').value,
                    tz: document.getElementById('vc-tz').value,
                    lang: document.getElementById('vc-lang').value,
                    source: document.getElementById('vc-source').value,
                    related: document.getElementById('vc-related').value
                };
                formData.append('content_data', JSON.stringify(vcardData));
            } else {
                formData.append('content_data', document.getElementById('content-data').value);
            }
            
            // Routing
            formData.append('ios_url', document.getElementById('ios-url').value);
            formData.append('android_url', document.getElementById('android-url').value);
            formData.append('ab_urls', document.getElementById('ab-urls').value);
            formData.append('geo_restrictions', document.getElementById('geo-restrictions').value);
            formData.append('time_day', document.getElementById('time-day').value);
            formData.append('time_night', document.getElementById('time-night').value);
            
            // Security
            formData.append('password', document.getElementById('password').value);
            formData.append('is_one_time', document.getElementById('one-time').checked);
            formData.append('scan_limit', document.getElementById('scan-limit').value);
            formData.append('expiry_datetime', document.getElementById('expiry').value);
            
            // Brand
            const logo = document.getElementById('logo-file').files[0];
            if (logo) formData.append('logo', logo);
            formData.append('qr_color', document.getElementById('qr-color').value);
            formData.append('bg_color', document.getElementById('bg-color').value);
            
            try {
                let url = '/api/generate';
                if (currentEditQrId) url = `/api/update/${currentEditQrId}`;

                const res = await fetch(url, {
                    method: 'POST',
                    body: formData
                });
                if (res.status === 401) {
                    checkSession();
                    return;
                }
                const data = await res.json();
                
                if(data.success) {
                    if(currentEditQrId) {
                        alert(data.message);
                        currentEditQrId = null;
                        document.getElementById('btn-generate').innerText = 'Generate Holographic QR ✨';
                        document.getElementById('page-title').innerText = 'Dashboard';
                        document.getElementById('page-subtitle').innerText = 'Create and route dynamic QR codes.';
                        switchTab('manage');
                    } else {
                        document.getElementById('result-container').style.display = 'block';
                        document.getElementById('qr-result-img').src = data.image_url;
                        document.getElementById('qr-result-text').innerText = data.message;
                    }
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (err) {
                alert('API Error: ' + err);
            }
        });

        // -----------------------------
        // QR Management Logic
        // -----------------------------
        async function loadQRCodes() {
            try {
                const res = await fetch('/api/list');
                if (res.status === 401) {
                    checkSession();
                    return;
                }
                const data = await res.json();
                if(data.success) {
                    const tbody = document.getElementById('qr-list-body');
                    const galleryGrid = document.getElementById('qr-gallery-grid');
                    tbody.innerHTML = '';
                    if (galleryGrid) galleryGrid.innerHTML = '';
                    
                    data.qrs.forEach(qr => {
                        const tr = document.createElement('tr');
                        tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                        tr.innerHTML = `
                            <td style="padding: 12px;"><input type="checkbox" class="qr-checkbox" value="${qr.qr_id}" style="accent-color: #ff3366; cursor: pointer; width: 16px; height: 16px;"></td>
                            <td style="padding: 12px; font-family: monospace; color: #00d4ff;">${qr.qr_id}</td>
                            <td style="padding: 12px; text-transform: uppercase; font-size: 12px;">${qr.content_type}</td>
                            <td style="padding: 12px;">${qr.current_scans} ${qr.scan_limit ? '/ ' + qr.scan_limit : ''}</td>
                            <td style="padding: 12px; display: flex; gap: 10px;">
                                <button onclick="showAnalytics('${qr.qr_id}')" style="background: #e6f0ff; color: #0052cc; border: 1px solid #0052cc; padding: 5px 10px; border-radius: 5px; cursor: pointer;">📊 Analytics</button>
                                <button onclick='editQR(${JSON.stringify(qr).replace(/'/g, "&#39;")})' style="background: #1a1b26; color: #fff; border: 1px solid #7000ff; padding: 5px 10px; border-radius: 5px; cursor: pointer;">Edit</button>
                                <button onclick="deleteQR('${qr.qr_id}')" style="background: #1a1b26; color: #ff3366; border: 1px solid #ff3366; padding: 5px 10px; border-radius: 5px; cursor: pointer;">Delete</button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                        
                        if (galleryGrid) {
                            const card = document.createElement('div');
                            card.className = 'card'; // Utilize global card styling
                            card.style.background = '#ffffff';
                            card.style.border = '1px solid rgba(0,0,0,0.05)';
                            card.style.borderRadius = '16px';
                            card.style.padding = '15px';
                            card.style.textAlign = 'center';
                            card.style.boxShadow = '0 10px 30px rgba(0,0,0,0.05)';
                            card.style.transition = 'transform 0.3s ease, box-shadow 0.3s ease';
                            card.onmouseover = () => { card.style.transform = 'translateY(-5px)'; card.style.boxShadow = '0 15px 35px rgba(0,0,0,0.1)'; };
                            card.onmouseout = () => { card.style.transform = 'translateY(0)'; card.style.boxShadow = '0 10px 30px rgba(0,0,0,0.05)'; };
                            
                            card.innerHTML = `
                                <img src="/qrcodes/${qr.qr_id}.png" style="width: 100%; border-radius: 8px; margin-bottom: 10px;">
                                <div style="font-family: monospace; font-size: 14px; font-weight: bold; color: #333;">${qr.qr_id}</div>
                                <div style="font-size: 12px; color: #666; margin-top: 5px;">Type: ${qr.content_type.toUpperCase()}</div>
                            `;
                            galleryGrid.appendChild(card);
                        }
                    });
                }
            } catch (err) {
                console.error(err);
            }
        }

        function editQR(qr) {
            currentEditQrId = qr.qr_id;
            
            // Switch to dashboard
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-dashboard').classList.add('active');
            document.getElementById('page-title').innerText = 'Update QR Code';
            document.getElementById('page-subtitle').innerText = `Editing QR ID: ${currentEditQrId}`;
            document.getElementById('btn-generate').innerText = 'Update Existing QR Code 🔄';
            
            // Populate Basic
            document.getElementById('qr-type').value = qr.content_type;
            document.getElementById('qr-type').dispatchEvent(new Event('change'));
            
            if (qr.content_type === 'vcard') {
                try {
                    const vd = JSON.parse(qr.content_data);
                    const fields = ['fn','ln','prefix','suffix','photo','company','title','dept','role','mobile','work','email','website','linkedin','github','whatsapp','street','city','state','zip','country','bday','notes','uid','rev','kind','geo','tz','lang','source','related'];
                    fields.forEach(f => {
                        if(document.getElementById('vc-' + f)) document.getElementById('vc-' + f).value = vd[f] || '';
                    });
                } catch(e){}
            } else if (qr.content_type !== 'pdf') {
                document.getElementById('content-data').value = qr.content_data;
            }
            
            // Populate Routing
            if (qr.device_redirects) {
                try {
                    const dr = JSON.parse(qr.device_redirects);
                    document.getElementById('ios-url').value = dr.ios || '';
                    document.getElementById('android-url').value = dr.android || '';
                } catch(e){}
            } else {
                document.getElementById('ios-url').value = '';
                document.getElementById('android-url').value = '';
            }
            
            if (qr.ab_testing_urls) {
                try {
                    const ab = JSON.parse(qr.ab_testing_urls);
                    document.getElementById('ab-urls').value = ab.join(', ');
                } catch(e){}
            } else {
                document.getElementById('ab-urls').value = '';
            }
            
            document.getElementById('geo-restrictions').value = qr.geo_restrictions || '';
            
            if (qr.time_routing) {
                try {
                    const tr = JSON.parse(qr.time_routing);
                    document.getElementById('time-day').value = tr.day || '';
                    document.getElementById('time-night').value = tr.night || '';
                } catch(e){}
            } else {
                document.getElementById('time-day').value = '';
                document.getElementById('time-night').value = '';
            }
            
            // Populate Security
            document.getElementById('password').value = qr.password || '';
            document.getElementById('expiry').value = qr.expiry_datetime || '';
            document.getElementById('scan-limit').value = qr.scan_limit || '';
            document.getElementById('one-time').checked = qr.is_one_time === 1;
            
            // Note: Logo and colors are baked into the image and aren't easy to edit retroactively without regenerating the image. 
            // The update API only updates the database routing logic.
        }

        async function deleteQR(id) {
            if(!confirm(`Are you sure you want to permanently delete QR Code ${id}?`)) return;
            try {
                const res = await fetch(`/api/delete/${id}`, { method: 'DELETE' });
                const data = await res.json();
                if(data.success) {
                    loadQRCodes();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (err) {
                alert('API Error: ' + err);
            }
        }

        function toggleSelectAll() {
            const isChecked = document.getElementById('select-all').checked;
            document.querySelectorAll('.qr-checkbox').forEach(cb => {
                cb.checked = isChecked;
            });
        }

        async function deleteSelected() {
            const selected = Array.from(document.querySelectorAll('.qr-checkbox:checked')).map(cb => cb.value);
            if(selected.length === 0) {
                alert("Please select at least one QR code to delete.");
                return;
            }
            if(!confirm(`Are you sure you want to permanently delete ${selected.length} QR Code(s)?`)) return;
            
            try {
                const res = await fetch('/api/delete_bulk', { 
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({qr_ids: selected})
                });
                const data = await res.json();
                if(data.success) {
                    document.getElementById('select-all').checked = false;
                    loadQRCodes();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (err) {
                alert('API Error: ' + err);
            }
        }

        // Analytics Functions
        let charts = {};
        
        function closeAnalyticsModal() {
            document.getElementById('analytics-modal').style.display = 'none';
        }
        
        async function showAnalytics(qr_id) {
            document.getElementById('analytics-modal').style.display = 'flex';
            document.getElementById('analytics-title').innerText = 'Loading Analytics...';
            
            try {
                const res = await fetch(`/api/analytics/${qr_id}`);
                const data = await res.json();
                
                if (data.success) {
                    document.getElementById('analytics-title').innerText = `Analytics for QR: ${qr_id}`;
                    document.getElementById('analytics-total').innerText = data.total_scans;
                    
                    // Render Recent Scans
                    const tbody = document.getElementById('recent-scans-body');
                    tbody.innerHTML = '';
                    data.recent_scans.forEach(scan => {
                        tbody.innerHTML += `
                            <tr style="border-bottom: 1px solid #eee;">
                                <td style="padding: 10px; color: #666;">${new Date(scan.timestamp).toLocaleString()}</td>
                                <td style="padding: 10px;">${scan.platform}</td>
                                <td style="padding: 10px;">${scan.os}</td>
                                <td style="padding: 10px;">${scan.browser}</td>
                                <td style="padding: 10px;">${scan.city}, ${scan.country}</td>
                            </tr>
                        `;
                    });
                    
                    // Destroy old charts if exist
                    ['timeChart', 'osChart', 'browserChart'].forEach(id => {
                        if (charts[id]) charts[id].destroy();
                    });
                    
                    // Prepare colors
                    const colors = ['#0052cc', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'];
                    
                    // Time Chart
                    const timeCtx = document.getElementById('timeChart').getContext('2d');
                    charts['timeChart'] = new Chart(timeCtx, {
                        type: 'line',
                        data: {
                            labels: Object.keys(data.scans_over_time).reverse(),
                            datasets: [{
                                label: 'Scans',
                                data: Object.values(data.scans_over_time).reverse(),
                                borderColor: '#0052cc',
                                backgroundColor: 'rgba(0, 82, 204, 0.1)',
                                tension: 0.3, fill: true
                            }]
                        }
                    });
                    
                    // OS Chart
                    const osCtx = document.getElementById('osChart').getContext('2d');
                    charts['osChart'] = new Chart(osCtx, {
                        type: 'doughnut',
                        data: {
                            labels: Object.keys(data.oses),
                            datasets: [{ data: Object.values(data.oses), backgroundColor: colors }]
                        },
                        options: { maintainAspectRatio: false }
                    });
                    
                    // Browser Chart
                    const browserCtx = document.getElementById('browserChart').getContext('2d');
                    charts['browserChart'] = new Chart(browserCtx, {
                        type: 'doughnut',
                        data: {
                            labels: Object.keys(data.browsers),
                            datasets: [{ data: Object.values(data.browsers), backgroundColor: colors }]
                        },
                        options: { maintainAspectRatio: false }
                    });
                    
                } else {
                    document.getElementById('analytics-title').innerText = 'Error loading analytics';
                }
            } catch (err) {
                console.error(err);
                document.getElementById('analytics-title').innerText = 'Failed to load analytics';
            }
        }

        // Forgot Password Logic
        function openForgotPasswordModal() {
            document.getElementById('forgot-password-modal').style.display = 'flex';
            document.getElementById('forgot-step-1').style.display = 'block';
            document.getElementById('forgot-step-2').style.display = 'none';
        }
        
        function closeForgotPasswordModal() {
            document.getElementById('forgot-password-modal').style.display = 'none';
        }
        
        async function requestPasswordReset() {
            const email = document.getElementById('forgot-email').value;
            if (!email) return alert('Please enter your email.');
            
            try {
                const res = await fetch('/api/forgot-password', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email})
                });
                const data = await res.json();
                if (data.success) {
                    alert('If the email is registered, a 6-digit code has been sent (check server console).');
                    document.getElementById('forgot-step-1').style.display = 'none';
                    document.getElementById('forgot-step-2').style.display = 'block';
                } else {
                    alert(data.error);
                }
            } catch (err) {
                console.error(err);
            }
        }
        
        async function submitNewPassword() {
            const email = document.getElementById('forgot-email').value;
            const token = document.getElementById('forgot-code').value;
            const new_password = document.getElementById('forgot-new-password').value;
            
            if (!token || !new_password) return alert('Please enter the code and a new password.');
            
            try {
                const res = await fetch('/api/reset-password', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email, token, new_password})
                });
                const data = await res.json();
                if (data.success) {
                    alert('Password reset successfully! You can now log in.');
                    closeForgotPasswordModal();
                } else {
                    alert(data.error || 'Failed to reset password.');
                }
            } catch (err) {
                console.error(err);
            }
        }

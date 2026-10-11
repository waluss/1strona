import { api } from './api.js';
import { escapeHtml, formatDate } from './utils.js';

const mainContent = document.getElementById('main-content');
const navbar = document.getElementById('navbar');
const userDisplay = document.getElementById('user-display');
const logoutBtn = document.getElementById('logout-btn');

let currentUser = null;

async function init() {
    window.addEventListener('hashchange', handleRoute);
    logoutBtn.addEventListener('click', handleLogout);

    if (localStorage.getItem('access_token')) {
        try {
            currentUser = await api.getMe();
            updateNavbar();
            handleRoute();
        } catch (e) {
            navigate('#login');
        }
    } else {
        navigate('#login');
    }
}

function navigate(hash) {
    window.location.hash = hash;
}

function updateNavbar() {
    if (currentUser) {
        navbar.classList.remove('hidden');
        userDisplay.textContent = `${currentUser.username} (${currentUser.is_admin ? 'Admin' : 'User'})`;
        if (currentUser.is_admin) {
            document.getElementById('nav-admin').classList.remove('hidden');
        }
    } else {
        navbar.classList.add('hidden');
    }
}

function handleLogout() {
    api.clearTokens();
    currentUser = null;
    updateNavbar();
    navigate('#login');
}

async function handleRoute() {
    const hash = window.location.hash || '#tenders';

    if (!localStorage.getItem('access_token') && hash !== '#login') {
        navigate('#login');
        return;
    }

    if (currentUser && currentUser.must_change_password && hash !== '#change-password') {
        navigate('#change-password');
        return;
    }

    if (hash === '#login') {
        renderLogin();
    } else if (hash === '#change-password') {
        renderChangePassword();
    } else if (hash.startsWith('#tenders/')) {
        const id = hash.split('/')[1];
        renderTenderDetails(id);
    } else if (hash === '#tenders') {
        renderTenderList();
    } else if (hash === '#profiles') {
        renderProfiles();
    } else if (hash === '#imports') {
        renderImports();
    } else if (hash === '#admin') {
        renderAdmin();
    }
}

// 1. LOGIN VIEW
function renderLogin() {
    mainContent.innerHTML = `
        <div style="max-width: 400px; margin: 80px auto;" class="card">
            <h2 class="card-title" style="text-align: center;">TenderPlatform Login</h2>
            <div id="login-error" style="color: red; margin-bottom: 10px;" class="hidden"></div>
            <form id="login-form">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" id="username" class="form-control" required value="admin">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="password" class="form-control" required value="admin">
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">Log In</button>
            </form>
        </div>
    `;

    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errDiv = document.getElementById('login-error');

        try {
            const res = await api.login(username, password);
            api.setTokens(res.access_token, res.refresh_token);
            currentUser = await api.getMe();
            updateNavbar();
            if (res.must_change_password) {
                navigate('#change-password');
            } else {
                navigate('#tenders');
            }
        } catch (err) {
            errDiv.textContent = escapeHtml(err.message);
            errDiv.classList.remove('hidden');
        }
    });
}

// 2. CHANGE PASSWORD VIEW
function renderChangePassword() {
    mainContent.innerHTML = `
        <div style="max-width: 400px; margin: 80px auto;" class="card">
            <h2 class="card-title" style="text-align: center;">Change Password Required</h2>
            <p style="margin-bottom: 15px; color: #666; font-size: 0.9rem;">You must change your default password before proceeding.</p>
            <div id="pwd-error" style="color: red; margin-bottom: 10px;" class="hidden"></div>
            <form id="pwd-form">
                <div class="form-group">
                    <label>Current Password</label>
                    <input type="password" id="old-pwd" class="form-control" required>
                </div>
                <div class="form-group">
                    <label>New Password</label>
                    <input type="password" id="new-pwd" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">Update Password</button>
            </form>
        </div>
    `;

    document.getElementById('pwd-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const oldPwd = document.getElementById('old-pwd').value;
        const newPwd = document.getElementById('new-pwd').value;
        const errDiv = document.getElementById('pwd-error');

        try {
            await api.changePassword(oldPwd, newPwd);
            currentUser.must_change_password = false;
            navigate('#tenders');
        } catch (err) {
            errDiv.textContent = escapeHtml(err.message);
            errDiv.classList.remove('hidden');
        }
    });
}

// 3. TENDER LIST VIEW WITH FILTERS
async function renderTenderList() {
    mainContent.innerHTML = `
        <div class="card">
            <h2 class="card-title">Procurement Notices Explorer</h2>
            <div class="filters-bar">
                <div class="form-group">
                    <label>Search Title/Buyer</label>
                    <input type="text" id="filter-search" class="form-control" placeholder="Search...">
                </div>
                <div class="form-group">
                    <label>Voivodeship</label>
                    <input type="text" id="filter-voivodeship" class="form-control" placeholder="e.g. Mazowieckie">
                </div>
                <div class="form-group">
                    <label>Match Decision</label>
                    <select id="filter-match" class="form-control">
                        <option value="">All Notices</option>
                        <option value="MATCH">Matches Only</option>
                        <option value="MANUAL_REVIEW">Manual Review</option>
                        <option value="REJECT">Rejected Only</option>
                    </select>
                </div>
                <div class="form-group" style="display: flex; align-items: flex-end;">
                    <button id="apply-filters" class="btn btn-primary" style="width: 100%;">Filter</button>
                </div>
            </div>

            <table class="table">
                <thead>
                    <tr>
                        <th>Title</th>
                        <th>Buyer</th>
                        <th>Voivodeship</th>
                        <th>Deadline</th>
                        <th>Published</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="tenders-tbody">
                    <tr><td colspan="6">Loading tenders...</td></tr>
                </tbody>
            </table>
        </div>
    `;

    const loadTenders = async () => {
        const search = document.getElementById('filter-search').value;
        const voivodeship = document.getElementById('filter-voivodeship').value;
        const match = document.getElementById('filter-match').value;

        const params = {};
        if (search) params.search = search;
        if (voivodeship) params.voivodeship = voivodeship;
        if (match) params.match_result = match;

        try {
            const tenders = await api.getTenders(params);
            const tbody = document.getElementById('tenders-tbody');
            if (tenders.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6">No procurement notices found.</td></tr>';
                return;
            }

            tbody.innerHTML = tenders.map(t => `
                <tr>
                    <td><strong>${escapeHtml(t.title)}</strong></td>
                    <td>${escapeHtml(t.buyer_name || 'N/A')}</td>
                    <td>${escapeHtml(t.location_voivodeship || 'All Poland')}</td>
                    <td>${formatDate(t.submission_deadline_at)}</td>
                    <td>${formatDate(t.source_published_at)}</td>
                    <td>
                        <a href="#tenders/${t.id}" class="btn btn-sm btn-outline">Details</a>
                    </td>
                </tr>
            `).join('');
        } catch (err) {
            console.error(err);
        }
    };

    document.getElementById('apply-filters').addEventListener('click', loadTenders);
    loadTenders();
}

// 4. TENDER DETAILS & REVISIONS VIEW
async function renderTenderDetails(id) {
    mainContent.innerHTML = '<div class="card">Loading tender details...</div>';
    try {
        const tender = await api.getTenderDetails(id);
        const notices = await api.getTenderNotices(id);
        const scores = await api.getTenderScores(id);

        mainContent.innerHTML = `
            <div class="card">
                <a href="#tenders" class="btn btn-sm btn-outline" style="margin-bottom: 15px; display: inline-block;">&larr; Back to Tenders</a>
                <h2 class="card-title">${escapeHtml(tender.title)}</h2>
                <p><strong>Buyer:</strong> ${escapeHtml(tender.buyer_name || 'N/A')} (NIP: ${escapeHtml(tender.buyer_nip || 'N/A')})</p>
                <p><strong>Location:</strong> ${escapeHtml(tender.location_voivodeship || 'N/A')}</p>
                <p><strong>Submission Deadline:</strong> ${formatDate(tender.submission_deadline_at)}</p>
                <p><strong>CPV Codes:</strong> ${escapeHtml((tender.cpv_codes || []).join(', '))}</p>
                <p><strong>Estimated Net Value:</strong> ${tender.estimated_value_net ? tender.estimated_value_net.toLocaleString() + ' PLN' : 'N/A'}</p>
            </div>

            <div class="card">
                <h3 class="card-title">Contractor Scoring & Explanations</h3>
                ${scores.length === 0 ? '<p>No active contractor profile scores evaluated for this tender yet.</p>' :
                    scores.map(s => `
                        <div style="padding: 12px; border: 1px solid #e2e8f0; border-radius: 6px; margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <strong>Decision: <span class="badge ${s.decision === 'MATCH' ? 'badge-match' : s.decision === 'MANUAL_REVIEW' ? 'badge-review' : 'badge-reject'}">${escapeHtml(s.decision)}</span></strong>
                                <span>Score: ${s.score}/100</span>
                            </div>
                            <p style="margin-top: 8px; font-size: 0.9rem;"><strong>Explanations:</strong></p>
                            <ul style="padding-left: 20px; font-size: 0.9rem; color: #475569;">
                                ${(s.breakdown.reasons || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}
                            </ul>
                        </div>
                    `).join('')
                }
            </div>

            <div class="card">
                <h3 class="card-title">Cleaned Order Description</h3>
                <div style="background: #f8fafc; padding: 15px; border-radius: 6px; font-family: monospace; font-size: 0.9rem; white-space: pre-wrap;">
                    ${escapeHtml(tender.raw_notice ? tender.raw_notice.orderObject || JSON.stringify(tender.raw_notice, null, 2) : 'No description available')}
                </div>
            </div>

            <div class="card">
                <h3 class="card-title">Notice History & Revisions</h3>
                ${notices.map(n => `
                    <div style="margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee;">
                        <p><strong>Notice ID:</strong> ${escapeHtml(n.notice_id)} | <strong>Kind:</strong> ${escapeHtml(n.notice_kind || 'N/A')} | <strong>Published:</strong> ${formatDate(n.published_at)}</p>
                        ${n.is_delta ? '<span class="badge badge-review">Delta Revision Updated</span>' : ''}
                    </div>
                `).join('')}
            </div>
        `;
    } catch (err) {
        mainContent.innerHTML = `<div class="card" style="color: red;">Error loading tender: ${escapeHtml(err.message)}</div>`;
    }
}

// 5. PROFILES VIEW
async function renderProfiles() {
    mainContent.innerHTML = `
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h2 class="card-title">Contractor Profiles</h2>
                <button id="show-create-profile" class="btn btn-primary">+ Create Profile</button>
            </div>
            <div id="profiles-list">Loading profiles...</div>
        </div>

        <div id="create-profile-modal" class="card hidden">
            <h3 class="card-title">Create New Contractor Profile</h3>
            <form id="profile-form">
                <div class="form-group">
                    <label>Profile Name</label>
                    <input type="text" id="prof-name" class="form-control" required placeholder="e.g. Water Supply Infrastructure Specialist">
                </div>
                <div class="form-group">
                    <label>Keywords (comma-separated)</label>
                    <input type="text" id="prof-keywords" class="form-control" placeholder="water supply, sewage, pipeline">
                </div>
                <div class="form-group">
                    <label>Exclusions (comma-separated)</label>
                    <input type="text" id="prof-exclusions" class="form-control" placeholder="gas, electrical">
                </div>
                <div class="form-group">
                    <label>CPV Codes (comma-separated)</label>
                    <input type="text" id="prof-cpvs" class="form-control" placeholder="45231300-8, 45232410-9">
                </div>
                <div class="form-group">
                    <label>Regions / Voivodeships (comma-separated)</label>
                    <input type="text" id="prof-regions" class="form-control" placeholder="Mazowieckie, Śląskie">
                </div>
                <button type="submit" class="btn btn-primary">Save Profile</button>
            </form>
        </div>
    `;

    const loadProfiles = async () => {
        try {
            const profiles = await api.getProfiles();
            const container = document.getElementById('profiles-list');
            if (profiles.length === 0) {
                container.innerHTML = '<p>No active contractor profiles found. Create one to begin tender scoring.</p>';
                return;
            }

            container.innerHTML = profiles.map(p => `
                <div style="border: 1px solid #cbd5e1; border-radius: 6px; padding: 15px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin-bottom: 4px;">${escapeHtml(p.name)} <span class="badge ${p.status === 'active' ? 'badge-match' : 'badge-review'}">${escapeHtml(p.status)}</span></h4>
                        <p style="font-size: 0.85rem; color: #64748b;">Keywords: ${escapeHtml((p.keywords || []).join(', '))}</p>
                    </div>
                    <div>
                        ${p.status === 'candidate' ? `<button data-id="${p.id}" class="btn btn-sm btn-primary activate-btn">Activate</button>` : ''}
                    </div>
                </div>
            `).join('');

            document.querySelectorAll('.activate-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.getAttribute('data-id');
                    await api.activateProfile(id);
                    loadProfiles();
                });
            });
        } catch (err) {
            console.error(err);
        }
    };

    document.getElementById('show-create-profile').addEventListener('click', () => {
        document.getElementById('create-profile-modal').classList.remove('hidden');
    });

    document.getElementById('profile-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            name: document.getElementById('prof-name').value,
            keywords: document.getElementById('prof-keywords').value.split(',').map(s => s.trim()).filter(Boolean),
            exclusions: document.getElementById('prof-exclusions').value.split(',').map(s => s.trim()).filter(Boolean),
            cpv_codes: document.getElementById('prof-cpvs').value.split(',').map(s => s.trim()).filter(Boolean),
            regions: document.getElementById('prof-regions').value.split(',').map(s => s.trim()).filter(Boolean),
            status: 'active'
        };

        try {
            await api.createProfile(data);
            document.getElementById('create-profile-modal').classList.add('hidden');
            loadProfiles();
        } catch (err) {
            alert(err.message);
        }
    });

    loadProfiles();
}

// 6. IMPORTS & DRY-RUN VIEW
async function renderImports() {
    mainContent.innerHTML = `
        <div class="card">
            <h2 class="card-title">BZP Import & Dry-Run Studio</h2>
            <div class="filters-bar">
                <div class="form-group">
                    <label>Notice Type</label>
                    <select id="imp-type" class="form-control">
                        <option value="">All Notice Types</option>
                        <option value="OgloszenieOZamowieniu">Ogłoszenie o zamówieniu</option>
                        <option value="OgloszenieOWynikuPostepowania">Ogłoszenie o wyniku postępowania</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Max Pages</label>
                    <input type="number" id="imp-pages" class="form-control" value="1" min="1" max="5">
                </div>
                <div class="form-group" style="display: flex; gap: 10px; align-items: flex-end;">
                    <button id="run-dryrun-btn" class="btn btn-outline" style="flex: 1;">Run Dry-Run</button>
                    <button id="run-liveimport-btn" class="btn btn-primary" style="flex: 1;">Run Live Import</button>
                </div>
            </div>

            <div id="import-results" class="hidden" style="margin-top: 20px;">
                <h3 class="card-title">Results</h3>
                <pre id="import-json" style="background: #1e293b; color: #f8fafc; padding: 15px; border-radius: 6px; max-height: 400px; overflow: auto;"></pre>
            </div>
        </div>
    `;

    document.getElementById('run-dryrun-btn').addEventListener('click', async () => {
        const type = document.getElementById('imp-type').value;
        const pages = document.getElementById('imp-pages').value;
        const resDiv = document.getElementById('import-results');
        const jsonPre = document.getElementById('import-json');

        try {
            const params = { max_pages: pages };
            if (type) params.notice_type = type;
            const res = await api.runDryRun(params);
            resDiv.classList.remove('hidden');
            jsonPre.textContent = JSON.stringify(res, null, 2);
        } catch (err) {
            alert(err.message);
        }
    });

    document.getElementById('run-liveimport-btn').addEventListener('click', async () => {
        const type = document.getElementById('imp-type').value;
        const pages = document.getElementById('imp-pages').value;
        const resDiv = document.getElementById('import-results');
        const jsonPre = document.getElementById('import-json');

        try {
            const params = { max_pages: pages };
            if (type) params.notice_type = type;
            const res = await api.runImport(params);
            resDiv.classList.remove('hidden');
            jsonPre.textContent = JSON.stringify(res, null, 2);
        } catch (err) {
            alert(err.message);
        }
    });
}

// 7. ADMIN VIEW
async function renderAdmin() {
    mainContent.innerHTML = `
        <div class="card">
            <h2 class="card-title">Tenant & Multi-Tenancy Management</h2>
            <div id="tenants-list">Loading tenants...</div>
        </div>
    `;

    try {
        const tenants = await api.getTenants();
        document.getElementById('tenants-list').innerHTML = `
            <table class="table">
                <thead>
                    <tr><th>Tenant ID</th><th>Name</th><th>Active</th><th>Created</th></tr>
                </thead>
                <tbody>
                    ${tenants.map(t => `
                        <tr>
                            <td><code>${escapeHtml(t.id)}</code></td>
                            <td>${escapeHtml(t.name)}</td>
                            <td>${t.is_active ? 'Yes' : 'No'}</td>
                            <td>${formatDate(t.created_at)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (err) {
        console.error(err);
    }
}

init();

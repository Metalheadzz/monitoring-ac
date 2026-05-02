const form = document.getElementById('login-form');
const errorEl = document.getElementById('login-error');

// If already logged in, redirect to dashboard
if (localStorage.getItem('auth_token')) {
    window.location.href = '/';
}

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const res = await fetch('http://localhost:5000/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (data.success && data.token) {
            // Save token
            localStorage.setItem('auth_token', data.token);
            // Redirect to dashboard
            window.location.href = '/';
        } else {
            showError(data.message || 'Invalid credentials');
        }
    } catch (err) {
        console.error(err);
        showError('Cannot connect to Server (API is down?)');
    }
});

function showError(msg) {
    errorEl.textContent = msg;
    errorEl.style.opacity = 1;
    setTimeout(() => {
        errorEl.style.opacity = 0;
    }, 3000);
}

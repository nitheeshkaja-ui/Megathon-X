```javascript
const loginForm = document.getElementById("loginForm");
const identifierInput = document.getElementById("identifier");
const passwordInput = document.getElementById("password");
const togglePassword = document.getElementById("togglePassword");
const loginButton = document.getElementById("loginButton");
const buttonText = document.getElementById("buttonText");
const loginMessage = document.getElementById("loginMessage");

// Clear login fields when opening or returning to this page.
// Browser password managers may still override this behavior.
function resetLoginForm() {
    loginForm.reset();
    identifierInput.value = "";
    passwordInput.value = "";
    passwordInput.type = "password";
    togglePassword.textContent = "Show";
    togglePassword.setAttribute("aria-label", "Show password");
    loginMessage.textContent = "";
    loginButton.disabled = false;
    buttonText.textContent = "Sign In";
}

window.addEventListener("pageshow", resetLoginForm);

// Show / hide password
togglePassword.addEventListener("click", () => {
    const showPassword = passwordInput.type === "password";

    passwordInput.type = showPassword ? "text" : "password";
    togglePassword.textContent = showPassword ? "Hide" : "Show";
    togglePassword.setAttribute(
        "aria-label",
        showPassword ? "Hide password" : "Show password"
    );
});

// Clear messages while typing
identifierInput.addEventListener("input", () => {
    loginMessage.textContent = "";
});

passwordInput.addEventListener("input", () => {
    loginMessage.textContent = "";
});

// Submit login
loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    loginMessage.textContent = "";

    const identifier = identifierInput.value.trim();
    const password = passwordInput.value;

    if (!identifier || !password) {
        loginMessage.textContent = "Please enter your ID and password.";
        return;
    }

    loginButton.disabled = true;
    buttonText.textContent = "Signing in...";

    try {
        // Keep this URL in sync with your existing backend route.
        const response = await fetch(
            "http://127.0.0.1:5000/api/auth/login",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username: identifier,
                    password: password
                })
            }
        );

        const data = await response.json().catch(() => ({}));

        if (!response.ok || data.success !== true) {
            throw new Error(
                data.message || "Invalid employee ID or password."
            );
        }

        // Use the user object returned by your backend.
        const user = data.user || {};

        // Store the authenticated user's returned data.
        // Do not store the password.
        const safeUser = { ...user };
        delete safeUser.password;

        localStorage.setItem("gciBankUser", JSON.stringify(safeUser));

        // Change this if your actual dashboard has another filename.
        window.location.href = "business.html";

    } catch (error) {
        loginMessage.textContent =
            error.message ||
            "Unable to connect to the server. Please try again.";

        loginButton.disabled = false;
        buttonText.textContent = "Sign In";
    }
});
```
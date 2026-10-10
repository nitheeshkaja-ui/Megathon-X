```javascript
const loginForm = document.getElementById("loginForm");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const togglePassword = document.getElementById("togglePassword");
const loginButton = document.getElementById("loginButton");
const buttonText = document.getElementById("buttonText");
const loginMessage = document.getElementById("loginMessage");

// Start with empty fields
function resetLoginForm() {
    loginForm.reset();

    emailInput.value = "";
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

// Clear errors when typing
emailInput.addEventListener("input", () => {
    loginMessage.textContent = "";
});

passwordInput.addEventListener("input", () => {
    loginMessage.textContent = "";
});

// Customer login
loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    loginMessage.textContent = "";

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
        loginMessage.textContent = "Please enter your email and password.";
        return;
    }

    loginButton.disabled = true;
    buttonText.textContent = "Signing in...";

    try {
        // Change this endpoint if your backend uses a different route.
        const response = await fetch(
            "http://127.0.0.1:5000/api/auth/login",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: email,
                    password: password
                })
            }
        );

        const data = await response.json().catch(() => ({}));

        if (!response.ok || data.success !== true) {
            throw new Error(
                data.message || "Invalid email or password."
            );
        }

        const user = data.user || {};

        // Ensure a customer account is used.
        const role = String(
            user.role || user.role_name || user.user_type || ""
        ).toLowerCase();

        if (role && !role.includes("customer")) {
            throw new Error("Please use a customer account to sign in.");
        }

        // Never save the password in localStorage.
        const safeUser = { ...user };
        delete safeUser.password;
        delete safeUser.token;

        localStorage.setItem(
            "gciCustomerUser",
            JSON.stringify(safeUser)
        );

        // Change this to your actual customer dashboard filename.
        window.location.href = "customer-dashboard.html";

    } catch (error) {
        loginMessage.textContent =
            error.message ||
            "Unable to connect to the server. Please try again.";

        loginButton.disabled = false;
        buttonText.textContent = "Sign In";
    }
});
```
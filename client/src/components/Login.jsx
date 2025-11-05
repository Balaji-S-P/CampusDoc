import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_URL } from "../config";

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    role: "student",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [darkMode, setDarkMode] = useState(false);
  const navigate = useNavigate();

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const endpoint = isLogin ? "/api/auth/login" : "/api/auth/register";
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (response.ok) {
        // Store user data in localStorage
        localStorage.setItem(
          "user",
          JSON.stringify({
            user_id: data.user_id,
            email: data.email,
            role: data.role,
          })
        );

        // Trigger a page reload to update authentication state
        window.location.href = "/chat";
      } else {
        setError(data.error || "An error occurred");
      }
    } catch (error) {
      setError("Network error. Please check if the server is running.");
      console.error("Login error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const styles = {
    container: {
      display: "flex",
      height: "100vh",
      width: "100vw",
      margin: 0,
      padding: 0,
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: darkMode ? "#343541" : "#ffffff",
      color: darkMode ? "#ffffff" : "#000000",
      position: "fixed",
      top: 0,
      left: 0,
      overflow: "hidden",
    },
    loginContainer: {
      display: "flex",
      flex: 1,
      alignItems: "center",
      justifyContent: "center",
      padding: "20px",
    },
    loginCard: {
      width: "100%",
      maxWidth: "400px",
      backgroundColor: darkMode ? "#40414f" : "#ffffff",
      borderRadius: "12px",
      padding: "32px",
      boxShadow: darkMode
        ? "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)"
        : "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
      border: `1px solid ${darkMode ? "#4d4d4f" : "#e5e5e5"}`,
    },
    header: {
      textAlign: "center",
      marginBottom: "32px",
    },
    title: {
      fontSize: "28px",
      fontWeight: "700",
      marginBottom: "8px",
      background: "linear-gradient(135deg, #3b82f6, #10a37f)",
      WebkitBackgroundClip: "text",
      WebkitTextFillColor: "transparent",
      backgroundClip: "text",
    },
    subtitle: {
      fontSize: "16px",
      color: darkMode ? "#8e8ea0" : "#6b7280",
      marginBottom: "0",
    },
    form: {
      display: "flex",
      flexDirection: "column",
      gap: "20px",
    },
    inputGroup: {
      display: "flex",
      flexDirection: "column",
      gap: "8px",
    },
    label: {
      fontSize: "14px",
      fontWeight: "500",
      color: darkMode ? "#ffffff" : "#374151",
    },
    input: {
      padding: "12px 16px",
      border: `1px solid ${darkMode ? "#4d4d4f" : "#d1d5db"}`,
      borderRadius: "8px",
      backgroundColor: darkMode ? "#343541" : "#ffffff",
      color: darkMode ? "#ffffff" : "#000000",
      fontSize: "16px",
      outline: "none",
      transition: "border-color 0.2s ease, box-shadow 0.2s ease",
    },
    inputFocus: {
      borderColor: "#3b82f6",
      boxShadow: "0 0 0 3px rgba(59, 130, 246, 0.1)",
    },
    select: {
      padding: "12px 16px",
      border: `1px solid ${darkMode ? "#4d4d4f" : "#d1d5db"}`,
      borderRadius: "8px",
      backgroundColor: darkMode ? "#343541" : "#ffffff",
      color: darkMode ? "#ffffff" : "#000000",
      fontSize: "16px",
      outline: "none",
      cursor: "pointer",
    },
    submitButton: {
      padding: "12px 24px",
      backgroundColor: "#3b82f6",
      color: "#ffffff",
      border: "none",
      borderRadius: "8px",
      fontSize: "16px",
      fontWeight: "600",
      cursor: "pointer",
      transition: "background-color 0.2s ease, transform 0.1s ease",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: "8px",
    },
    submitButtonHover: {
      backgroundColor: "#2563eb",
      transform: "translateY(-1px)",
    },
    submitButtonDisabled: {
      backgroundColor: darkMode ? "#4d4d4f" : "#d1d5db",
      cursor: "not-allowed",
      transform: "none",
    },
    toggleButton: {
      background: "none",
      border: "none",
      color: "#3b82f6",
      cursor: "pointer",
      fontSize: "14px",
      textDecoration: "underline",
      padding: "8px 0",
    },
    errorMessage: {
      backgroundColor: "#fef2f2",
      border: "1px solid #fecaca",
      color: "#dc2626",
      padding: "12px",
      borderRadius: "8px",
      fontSize: "14px",
      marginBottom: "16px",
    },
    errorMessageDark: {
      backgroundColor: "#7f1d1d",
      border: "1px solid #991b1b",
      color: "#fca5a5",
    },
    themeToggle: {
      position: "absolute",
      top: "20px",
      right: "20px",
      background: "none",
      border: "none",
      cursor: "pointer",
      fontSize: "24px",
      padding: "8px",
      borderRadius: "8px",
      color: darkMode ? "#ffffff" : "#000000",
      transition: "background-color 0.2s ease",
    },
    loadingSpinner: {
      width: "20px",
      height: "20px",
      border: "2px solid #ffffff",
      borderTop: "2px solid transparent",
      borderRadius: "50%",
      animation: "spin 1s linear infinite",
    },
  };

  return (
    <>
      <style>
        {`
          * {
            box-sizing: border-box;
          }
          
          html, body {
            margin: 0 !important;
            padding: 0 !important;
            height: 100% !important;
            width: 100% !important;
            overflow: hidden !important;
          }
          
          #root {
            height: 100vh !important;
            width: 100vw !important;
          }

          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
      <div style={styles.container}>
        <button
          style={styles.themeToggle}
          onClick={() => setDarkMode(!darkMode)}
          onMouseEnter={(e) =>
            (e.target.style.backgroundColor = darkMode ? "#2d2d30" : "#f3f4f6")
          }
          onMouseLeave={(e) => (e.target.style.backgroundColor = "transparent")}
        >
          {darkMode ? "☀️" : "🌙"}
        </button>

        <div style={styles.loginContainer}>
          <div style={styles.loginCard}>
            <div style={styles.header}>
              <h1 style={styles.title}>RAG Chat</h1>
              <p style={styles.subtitle}>
                {isLogin
                  ? "Welcome back! Sign in to continue"
                  : "Create your account to get started"}
              </p>
            </div>

            {error && (
              <div
                style={{
                  ...styles.errorMessage,
                  ...(darkMode ? styles.errorMessageDark : {}),
                }}
              >
                {error}
              </div>
            )}

            <form style={styles.form} onSubmit={handleSubmit}>
              <div style={styles.inputGroup}>
                <label style={styles.label} htmlFor="email">
                  Email Address
                </label>
                <input
                  style={styles.input}
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="Enter your email"
                  required
                  onFocus={(e) => {
                    e.target.style.borderColor = "#3b82f6";
                    e.target.style.boxShadow =
                      "0 0 0 3px rgba(59, 130, 246, 0.1)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = darkMode
                      ? "#4d4d4f"
                      : "#d1d5db";
                    e.target.style.boxShadow = "none";
                  }}
                />
              </div>

              <div style={styles.inputGroup}>
                <label style={styles.label} htmlFor="password">
                  Password
                </label>
                <input
                  style={styles.input}
                  type="password"
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  placeholder="Enter your password"
                  required
                  onFocus={(e) => {
                    e.target.style.borderColor = "#3b82f6";
                    e.target.style.boxShadow =
                      "0 0 0 3px rgba(59, 130, 246, 0.1)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = darkMode
                      ? "#4d4d4f"
                      : "#d1d5db";
                    e.target.style.boxShadow = "none";
                  }}
                />
              </div>

              {!isLogin && (
                <div style={styles.inputGroup}>
                  <label style={styles.label} htmlFor="role">
                    Role
                  </label>
                  <select
                    style={styles.select}
                    id="role"
                    name="role"
                    value={formData.role}
                    onChange={handleInputChange}
                  >
                    <option value="student">Student</option>
                    <option value="teacher">Teacher</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              )}

              <button
                type="submit"
                style={{
                  ...styles.submitButton,
                  ...(isLoading ? styles.submitButtonDisabled : {}),
                }}
                disabled={isLoading}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.target.style.backgroundColor = "#2563eb";
                    e.target.style.transform = "translateY(-1px)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isLoading) {
                    e.target.style.backgroundColor = "#3b82f6";
                    e.target.style.transform = "translateY(0)";
                  }
                }}
              >
                {isLoading && <div style={styles.loadingSpinner}></div>}
                {isLoading
                  ? "Processing..."
                  : isLogin
                  ? "Sign In"
                  : "Create Account"}
              </button>
            </form>

            <div style={{ textAlign: "center", marginTop: "24px" }}>
              <button
                style={styles.toggleButton}
                onClick={() => {
                  setIsLogin(!isLogin);
                  setError("");
                  setFormData({ email: "", password: "", role: "student" });
                }}
              >
                {isLogin
                  ? "Don't have an account? Sign up"
                  : "Already have an account? Sign in"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Login;

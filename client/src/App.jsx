import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Login from "./components/Login";
import { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is authenticated
    const user = localStorage.getItem("user");
    if (user) {
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          fontSize: "18px",
        }}
      >
        Loading...
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/chat" replace /> : <Login />}
      />
      <Route
        path="/chat"
        element={
          isAuthenticated ? <Layout /> : <Navigate to="/login" replace />
        }
      />
      <Route
        path="/chat/:chat_id"
        element={
          isAuthenticated ? <Layout /> : <Navigate to="/login" replace />
        }
      />
      <Route
        path="/"
        element={
          isAuthenticated ? (
            <Navigate to="/chat" replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  );
}

export default App;

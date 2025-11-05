import React, { useState, useEffect } from "react";
import CustomMarkDown from "./CustomMarkDown";
import { useParams, useNavigate } from "react-router-dom";
import FilesDialog from "./FilesDialog";
import FolderDialog from "./FolderDialog";

const Layout = () => {
  const params = useParams();
  const chat_id = params?.chat_id || null;
  const navigate = useNavigate();

  console.log("Layout rendered with params:", params);
  console.log("Chat ID extracted:", chat_id);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentMessage, setCurrentMessage] = useState("");
  const [activeThread, setActiveThread] = useState(chat_id);
  const [darkMode, setDarkMode] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState(null);
  const [showFilesDialog, setShowFilesDialog] = useState(false);
  const [showFolderDialog, setShowFolderDialog] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [selectedFolders, setSelectedFolders] = useState([]);
  // Sample chat threads
  const [chatThreads, setChatThreads] = useState([
    // {
    //   id: 0,
    //   title: "React Development Tips",
    //   lastMessage: "How to optimize React components?",
    // },
    // {
    //   id: 1,
    //   title: "JavaScript ES6 Features",
    //   lastMessage: "Explain arrow functions",
    // },
    // {
    //   id: 2,
    //   title: "CSS Grid vs Flexbox",
    //   lastMessage: "When should I use CSS Grid?",
    // },
    // {
    //   id: 3,
    //   title: "Node.js Best Practices",
    //   lastMessage: "Database connection patterns",
    // },
  ]);

  // Sample messages for active thread
  const [messages, setMessages] = useState([
    // {
    //   id: 1,
    //   type: "user",
    //   content: "How do I create a responsive sidebar in React?",
    // },
    // {
    //   id: 2,
    //   type: "assistant",
    //   content:
    //     "To create a responsive sidebar in React, you can use CSS Flexbox and media queries. Here's a basic approach:\n\n1. Use a flex container for the main layout\n2. Create a sidebar with responsive width\n3. Use useState to manage sidebar visibility on mobile\n4. Apply CSS media queries for different screen sizes\n\nWould you like me to show you a complete example?",
    // },
    // {
    //   id: 3,
    //   type: "user",
    //   content: "Yes, please show me a complete example with CSS",
    // },
  ]);
  useEffect(() => {
    if (activeThread) {
      fetch(`http://localhost:5001/chats/${activeThread}`)
        .then((response) => response.json())
        .then((data) => setMessages(data.chat.messages));
    }
  }, [activeThread]);

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files);
    if (files.length > 0) {
      setSelectedFiles(files);
    }
    // Clear the input so the same file can be selected again
    event.target.value = "";
  };

  const removeFile = (index) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSendMessage = async () => {
    if (!currentMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: "user",
      content: currentMessage,
    };

    // Add user message immediately
    setMessages((prev) => [...prev, userMessage]);
    const messageText = currentMessage;
    setCurrentMessage("");
    setIsLoading(true);

    try {
      // Call your RAG backend
      let response;
      if (selectedFiles.length > 0) {
        // If files are selected, send as FormData
        const formData = new FormData();
        formData.append("query", messageText);
        formData.append("chat_id", activeThread);
        formData.append("user_id", user.user_id);

        // Append each file
        selectedFiles.forEach((file, index) => {
          formData.append(`file_${index}`, file);
        });

        // Append selected folders
        selectedFolders.forEach((folderId) => {
          formData.append("selected_folders", folderId);
        });

        response = await fetch("http://localhost:5001/query", {
          method: "POST",
          body: formData,
        });
      } else {
        // Regular JSON request
        response = await fetch("http://localhost:5001/query", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: messageText,
            chat_id: activeThread,
            user_id: user.user_id,
            selected_folders: selectedFolders,
          }),
        });
      }

      const data = await response.json();

      if (data.response) {
        const assistantMessage = {
          id: Date.now() + 1,
          type: "assistant",
          content: data.response,
        };
        setMessages((prev) => [...prev, assistantMessage]);

        // Update activeThread if a new chat was created
        if (data.chat_id && !activeThread) {
          setActiveThread(data.chat_id);
          refreshChatThreads(); // Refresh the chat threads list
        }
        if (!activeThread) {
          navigate(`/chat/${data.chat_id}`);
        }

        // Clear selected files after successful send
        setSelectedFiles([]);
      } else {
        throw new Error(data.error || "Failed to get response");
      }
    } catch (error) {
      console.error("Error sending message:", error);
      // Add error message
      const errorMessage = {
        id: Date.now() + 1,
        type: "assistant",
        content: `Sorry, I encountered an error: ${error.message}. Please make sure the backend is running on port 5001.`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };
  useEffect(() => {
    console.log("Chat ID from URL:", chat_id);
    console.log("Current URL:", window.location.href);
    if (chat_id) {
      console.log("Setting active thread to:", chat_id);
      setActiveThread(chat_id);
    } else {
      console.log("Setting active thread to null");
      setActiveThread(null);
    }
  }, [chat_id]);

  // Function to refresh chat threads
  const refreshChatThreads = () => {
    fetch("http://localhost:5001/chat/threads")
      .then((response) => response.json())
      .then((data) => setChatThreads(data.threads))
      .catch((error) => console.error("Error loading chat threads:", error));
  };
  const createNewChat = () => {
    setActiveThread(null);
    setMessages([]);
    refreshChatThreads(); // Refresh chat threads
    navigate("/chat");
  };
  useEffect(() => {
    // Load user data from localStorage
    const userData = localStorage.getItem("user");
    if (userData) {
      setUser(JSON.parse(userData));
    }

    fetch("http://localhost:5001/chat/threads")
      .then((response) => response.json())
      .then((data) => setChatThreads(data.threads));
  }, []); // Load threads only once on component mount

  const handleLogout = () => {
    localStorage.removeItem("user");
    setUser(null);
    window.location.href = "/login";
  };
  const styles = {
    app: {
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
    sidebar: {
      width: sidebarOpen ? "280px" : "0",
      backgroundColor: darkMode ? "#202123" : "#f7f7f8",
      borderRight: `1px solid ${darkMode ? "#4d4d4f" : "#e5e5e5"}`,
      transition: "width 0.2s ease",
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
      position: "relative",
      zIndex: 10,
    },
    sidebarContent: {
      padding: "12px",
      display: "flex",
      flexDirection: "column",
      height: "100%",
    },
    newChatBtn: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: "8px",
      padding: "12px 16px",
      border: `1px solid ${darkMode ? "#4d4d4f" : "#d1d5db"}`,
      borderRadius: "8px",
      backgroundColor: "transparent",
      color: darkMode ? "#ffffff" : "#000000",
      cursor: "pointer",
      fontSize: "14px",
      fontWeight: "500",
      transition: "background-color 0.2s ease",
      marginBottom: "12px",
    },
    chatThreads: {
      flex: 1,
      overflowY: "auto",
      display: "flex",
      flexDirection: "column",
      gap: "4px",
    },
    chatThread: {
      padding: "12px",
      borderRadius: "8px",
      cursor: "pointer",
      transition: "background-color 0.2s ease",
      display: "flex",
      alignItems: "center",
      gap: "8px",
    },
    chatThreadActive: {
      backgroundColor: darkMode ? "#343541" : "#f3f4f6",
    },
    chatThreadContent: {
      flex: 1,
      minWidth: 0,
    },
    chatTitle: {
      fontSize: "14px",
      fontWeight: "500",
      marginBottom: "2px",
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
    },
    chatLastMessage: {
      fontSize: "12px",
      color: darkMode ? "#8e8ea0" : "#6b7280",
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
    },
    mainContent: {
      flex: 1,
      display: "flex",
      flexDirection: "column",
      minWidth: 0,
    },
    topBar: {
      display: "flex",
      alignItems: "center",
      padding: "12px 16px",
      borderBottom: `1px solid ${darkMode ? "#4d4d4f" : "#e5e5e5"}`,
      backgroundColor: darkMode ? "#343541" : "#ffffff",
      gap: "12px",
    },
    menuBtn: {
      background: "none",
      border: "none",
      cursor: "pointer",
      padding: "8px",
      borderRadius: "6px",
      color: darkMode ? "#ffffff" : "#000000",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: "18px",
    },
    topBarTitle: {
      flex: 1,
      textAlign: "center",
      fontSize: "18px",
      fontWeight: "600",
    },
    themeBtn: {
      background: "none",
      border: "none",
      cursor: "pointer",
      padding: "8px",
      borderRadius: "6px",
      color: darkMode ? "#ffffff" : "#000000",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: "16px",
    },
    messagesArea: {
      flex: 1,
      overflowY: "auto",
      padding: "16px",
    },
    messagesContainer: {
      maxWidth: "768px",
      margin: "0 auto",
      display: "flex",
      flexDirection: "column",
      gap: "24px",
    },
    messageRow: {
      display: "flex",
      alignItems: "flex-start",
      gap: "12px",
    },
    messageRowUser: {
      justifyContent: "flex-end",
    },
    avatar: {
      width: "32px",
      height: "32px",
      borderRadius: "50%",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: "14px",
      fontWeight: "600",
      color: "#ffffff",
    },
    avatarAssistant: {
      backgroundColor: "#10a37f",
    },
    avatarUser: {
      backgroundColor: "#3b82f6",
    },
    messageBubble: {
      maxWidth: "70%",
      padding: "12px 16px",
      borderRadius: "16px",
      whiteSpace: "pre-wrap",
      lineHeight: "1.5",
    },
    messageBubbleUser: {
      backgroundColor: "#3b82f6",
      color: "#ffffff",
    },
    messageBubbleAssistant: {
      backgroundColor: darkMode ? "#444654" : "#f7f7f8",
      color: darkMode ? "#ffffff" : "#000000",
    },
    inputArea: {
      padding: "16px",
      borderTop: `1px solid ${darkMode ? "#4d4d4f" : "#e5e5e5"}`,
      backgroundColor: darkMode ? "#343541" : "#ffffff",
    },
    inputContainer: {
      maxWidth: "768px",
      margin: "0 auto",
      position: "relative",
    },
    inputWrapper: {
      position: "relative",
      display: "flex",
      alignItems: "center",
    },
    input: {
      width: "100%",
      padding: "12px 50px 12px 16px",
      border: `1px solid ${darkMode ? "#4d4d4f" : "#d1d5db"}`,
      borderRadius: "24px",
      backgroundColor: darkMode ? "#40414f" : "#ffffff",
      color: darkMode ? "#ffffff" : "#000000",
      fontSize: "16px",
      outline: "none",
      resize: "none",
    },
    sendBtn: {
      position: "absolute",
      right: "8px",
      width: "32px",
      height: "32px",
      borderRadius: "16px",
      border: "none",
      backgroundColor: "#3b82f6",
      color: "#ffffff",
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: "16px",
      transition: "background-color 0.2s ease",
    },
    sendBtnDisabled: {
      backgroundColor: darkMode ? "#4d4d4f" : "#d1d5db",
      cursor: "not-allowed",
    },
    disclaimer: {
      fontSize: "12px",
      color: darkMode ? "#8e8ea0" : "#6b7280",
      textAlign: "center",
      marginTop: "8px",
    },
    typingIndicator: {
      display: "flex",
      gap: "4px",
      alignItems: "center",
    },
    filePreviewContainer: {
      padding: "10px",
      backgroundColor: darkMode ? "#2d3748" : "#f7fafc",
      borderBottom: `1px solid ${darkMode ? "#4a5568" : "#e2e8f0"}`,
      maxHeight: "120px",
      overflowY: "auto",
    },
    filePreviewTitle: {
      fontSize: "12px",
      fontWeight: "bold",
      color: darkMode ? "#a0aec0" : "#718096",
      marginBottom: "8px",
    },
    filePreviewItem: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "4px 8px",
      backgroundColor: darkMode ? "#4a5568" : "#edf2f7",
      borderRadius: "4px",
      marginBottom: "4px",
    },
    fileName: {
      fontSize: "12px",
      color: darkMode ? "#e2e8f0" : "#2d3748",
      flex: 1,
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap",
    },
    removeFileBtn: {
      background: "none",
      border: "none",
      color: darkMode ? "#ef4444" : "#dc2626",
      cursor: "pointer",
      fontSize: "16px",
      padding: "0 4px",
    },
    fileInput: {
      display: "none",
    },
    fileUploadBtn: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      width: "40px",
      height: "40px",
      backgroundColor: darkMode ? "#4a5568" : "#edf2f7",
      border: "none",
      borderRadius: "8px",
      cursor: "pointer",
      fontSize: "16px",
      marginRight: "8px",
      transition: "background-color 0.2s",
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
        `}
      </style>
      <div style={styles.app}>
        {/* Sidebar */}
        <div style={styles.sidebar}>
          <div style={styles.sidebarContent}>
            <button
              onClick={() => setShowFilesDialog(true)}
              style={styles.newChatBtn}
            >
              <span>📂</span>
              Files
              <FilesDialog
                showFilesDialog={showFilesDialog}
                setShowFilesDialog={setShowFilesDialog}
              />
            </button>
            <button
              onClick={() => setShowFolderDialog(true)}
              style={{
                ...styles.newChatBtn,
                backgroundColor: darkMode ? "#4a5568" : "#e2e8f0",
                color: darkMode ? "#ffffff" : "#2d3748",
                marginTop: "8px",
              }}
            >
              <span>📁</span>
              Smart Folders
              <FolderDialog
                showFolderDialog={showFolderDialog}
                setShowFolderDialog={setShowFolderDialog}
                selectedFolders={selectedFolders}
                setSelectedFolders={setSelectedFolders}
              />
            </button>
            <button
              style={{
                ...styles.newChatBtn,
                backgroundColor: darkMode ? "#4a5568" : "#e2e8f0",
                color: darkMode ? "#ffffff" : "#2d3748",
                marginTop: "8px",
              }}
              onClick={() =>
                window.open(
                  `http://localhost:5001/api/auth/authorize?user_id=${user.user_id}`,
                  "_blank"
                )
              }
            >
              🧪 Gmail
            </button>
            <button
              style={styles.newChatBtn}
              onClick={createNewChat}
              onMouseEnter={(e) =>
                (e.target.style.backgroundColor = darkMode
                  ? "#2d2d30"
                  : "#f3f4f6")
              }
              onMouseLeave={(e) =>
                (e.target.style.backgroundColor = "transparent")
              }
            >
              <span>➕</span>
              New Chat
            </button>

            <div style={styles.chatThreads}>
              {chatThreads.map((thread) => (
                <div
                  key={thread.id}
                  style={{
                    ...styles.chatThread,
                    ...(activeThread === thread.id
                      ? styles.chatThreadActive
                      : {}),
                  }}
                  onClick={() => {
                    console.log("Clicking thread:", thread.id);
                    console.log(
                      "Current URL before navigation:",
                      window.location.href
                    );
                    setActiveThread(thread.id);
                    navigate(`/chat/${thread.id}`);
                    console.log("Navigation called to:", `/chat/${thread.id}`);
                  }}
                  onMouseEnter={(e) => {
                    if (activeThread !== thread.id) {
                      e.target.style.backgroundColor = darkMode
                        ? "#2d2d30"
                        : "#f9fafb";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (activeThread !== thread.id) {
                      e.target.style.backgroundColor = "transparent";
                    }
                  }}
                >
                  <span>💬</span>
                  <div style={styles.chatThreadContent}>
                    <div style={styles.chatTitle}>{thread.title}</div>
                    <div style={styles.chatLastMessage}>
                      {thread.lastMessage}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div style={styles.mainContent}>
          {/* Top Bar */}
          <div style={styles.topBar}>
            <button
              style={styles.menuBtn}
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              ☰
            </button>

            <div style={styles.topBarTitle}>
              {chatThreads.find((t) => t.id === activeThread)?.title ||
                "Document Search"}
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              {user && (
                <span
                  style={{
                    fontSize: "14px",
                    color: darkMode ? "#8e8ea0" : "#6b7280",
                  }}
                >
                  {user.email}
                </span>
              )}
              <button
                style={styles.themeBtn}
                onClick={() => setDarkMode(!darkMode)}
              >
                {darkMode ? "☀️" : "🌙"}
              </button>
              <button
                style={{
                  ...styles.themeBtn,
                  backgroundColor: darkMode ? "#dc2626" : "#ef4444",
                  color: "#ffffff",
                  padding: "8px 12px",
                  fontSize: "12px",
                }}
                onClick={handleLogout}
                onMouseEnter={(e) =>
                  (e.target.style.backgroundColor = darkMode
                    ? "#b91c1c"
                    : "#dc2626")
                }
                onMouseLeave={(e) =>
                  (e.target.style.backgroundColor = darkMode
                    ? "#dc2626"
                    : "#ef4444")
                }
              >
                Logout
              </button>
            </div>
          </div>

          {/* Messages Area */}
          <div style={styles.messagesArea}>
            <div style={styles.messagesContainer}>
              {messages.map((message) => {
                // Handle both 'type' and 'role' properties for backward compatibility
                const messageType = message.type || message.role;
                const isUser = messageType === "user";
                const isAssistant = messageType === "assistant";

                return (
                  <div
                    key={message.id}
                    style={{
                      ...styles.messageRow,
                      ...(isUser ? styles.messageRowUser : {}),
                    }}
                  >
                    {isAssistant && (
                      <div
                        style={{ ...styles.avatar, ...styles.avatarAssistant }}
                      >
                        AI
                      </div>
                    )}
                    <div
                      style={{
                        ...styles.messageBubble,
                        ...(isUser
                          ? styles.messageBubbleUser
                          : styles.messageBubbleAssistant),
                      }}
                    >
                      {isAssistant ? (
                        <CustomMarkDown
                          content={message.content}
                          applyMarkDown={true}
                          codeBlockMarginY={2}
                        />
                      ) : (
                        message.content
                      )}
                    </div>
                    {isUser && (
                      <div style={{ ...styles.avatar, ...styles.avatarUser }}>
                        U
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Loading indicator */}
              {isLoading && (
                <div style={styles.messageRow}>
                  <div style={{ ...styles.avatar, ...styles.avatarAssistant }}>
                    AI
                  </div>
                  <div style={styles.messageBubbleAssistant}>
                    <div style={styles.typingIndicator}>
                      <span>●</span>
                      <span>●</span>
                      <span>●</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Input Area */}
          <div style={styles.inputArea}>
            {/* File Upload Section */}
            {selectedFiles.length > 0 && (
              <div style={styles.filePreviewContainer}>
                <div style={styles.filePreviewTitle}>Selected Files:</div>
                {selectedFiles.map((file, index) => (
                  <div key={index} style={styles.filePreviewItem}>
                    <span style={styles.fileName}>{file.name}</span>
                    <button
                      style={styles.removeFileBtn}
                      onClick={() => removeFile(index)}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Selected Smart Folders Indicator */}
            {selectedFolders.length > 0 && (
              <div
                style={{
                  padding: "8px 16px",
                  backgroundColor: darkMode ? "#2d3748" : "#e2e8f0",
                  borderBottom: "1px solid #e2e8f0",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  flexWrap: "wrap",
                }}
              >
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: "500",
                    color: darkMode ? "#a0aec0" : "#4a5568",
                  }}
                >
                  📁 Using Smart Folders:
                </span>
                {selectedFolders.map((folderId) => {
                  // We need to get the folder name, but we don't have access to folders here
                  // For now, just show the folder ID
                  return (
                    <span
                      key={folderId}
                      style={{
                        backgroundColor: darkMode ? "#4a5568" : "#ffffff",
                        color: darkMode ? "#ffffff" : "#2d3748",
                        padding: "2px 8px",
                        borderRadius: "12px",
                        fontSize: "11px",
                        border: "1px solid #cbd5e0",
                      }}
                    >
                      {folderId}
                    </span>
                  );
                })}
                <button
                  onClick={() => setSelectedFolders([])}
                  style={{
                    background: "none",
                    border: "none",
                    color: darkMode ? "#a0aec0" : "#4a5568",
                    cursor: "pointer",
                    fontSize: "12px",
                    padding: "2px 4px",
                  }}
                >
                  ✕ Clear
                </button>
              </div>
            )}

            <div style={styles.inputContainer}>
              <div style={styles.inputWrapper}>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.gif,.xls,.xlsx,.csv"
                  onChange={handleFileSelect}
                  style={styles.fileInput}
                  id="file-upload"
                />
                <label htmlFor="file-upload" style={styles.fileUploadBtn}>
                  📎
                </label>
                <input
                  style={styles.input}
                  type="text"
                  placeholder={
                    isLoading ? "AI is thinking..." : "Ask a question..."
                  }
                  value={currentMessage}
                  onChange={(e) => setCurrentMessage(e.target.value)}
                  onKeyPress={(e) =>
                    e.key === "Enter" && !isLoading && handleSendMessage()
                  }
                  disabled={isLoading}
                />
                <button
                  style={{
                    ...styles.sendBtn,
                    ...(currentMessage.trim() && !isLoading
                      ? {}
                      : styles.sendBtnDisabled),
                  }}
                  onClick={handleSendMessage}
                  disabled={!currentMessage.trim() || isLoading}
                >
                  {isLoading ? "⏳" : "↑"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Layout;

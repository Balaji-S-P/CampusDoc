import { API_URL } from "../config";
import {
  Table,
  Text,
  IconButton,
  HStack,
  VStack,
  Box,
  Badge,
  Spinner,
  Center,
} from "@chakra-ui/react";
import { useState, useEffect } from "react";
import { FiDownload, FiTrash2, FiFile } from "react-icons/fi";

const FilesList = () => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);

  // Get user_id with error handling
  const getUser = () => {
    try {
      const user = JSON.parse(localStorage.getItem("user"));
      return user?.user_id || null;
    } catch (error) {
      console.error("Error parsing user from localStorage:", error);
      return null;
    }
  };

  const user_id = getUser();
  const fetchFiles = async () => {
    try {
      setLoading(true);

      if (!user_id) {
        console.error("No user_id found in localStorage");
        alert("Please log in to view files");
        return;
      }

      console.log("Fetching files for user_id:", user_id);
      const response = await fetch(`${API_URL}/api/file/get_files/${user_id}`, {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        console.log("Files fetched successfully:", data);
        setFiles(data.files || []);
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.error || `HTTP ${response.status}: ${response.statusText}`
        );
      }
    } catch (error) {
      console.error("Error fetching files:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();

    // Listen for file updates
    const handleFilesUpdated = () => {
      fetchFiles();
    };

    window.addEventListener("filesUpdated", handleFilesUpdated);
    return () => window.removeEventListener("filesUpdated", handleFilesUpdated);
  }, []);

  const handleDeleteFile = async (file_id) => {
    try {
      const response = await fetch(
        `${API_URL}/api/file/delete_file/${user_id}/${file_id}`,
        {
          method: "DELETE",
          credentials: "include",
        }
      );

      if (response.ok) {
        alert("File deleted successfully");
        fetchFiles(); // Refresh the list
      } else {
        throw new Error("Failed to delete file");
      }
    } catch (error) {
      alert(`Failed to delete file: ${error.message}`);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getFileIcon = (filename) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (["pdf"].includes(ext)) return "📄";
    if (["jpg", "jpeg", "png", "gif"].includes(ext)) return "🖼️";
    if (["doc", "docx"].includes(ext)) return "📝";
    if (["xls", "xlsx"].includes(ext)) return "📊";
    if (["txt"].includes(ext)) return "📄";
    return "📁";
  };

  if (loading) {
    return (
      <Center py={8}>
        <VStack spacing={3}>
          <Spinner size="lg" color="blue.500" />
          <Text color="gray.500">Loading files...</Text>
        </VStack>
      </Center>
    );
  }

  if (files.length === 0) {
    return (
      <Center py={8}>
        <VStack spacing={3}>
          <Text fontSize="4xl">📁</Text>
          <Text color="gray.500" textAlign="center">
            No files uploaded yet
          </Text>
          <Text fontSize="sm" color="gray.400" textAlign="center">
            Upload some files to get started
          </Text>
        </VStack>
      </Center>
    );
  }

  return (
    <Box maxH="60vh" overflowY="auto">
      <Table.Root size="sm" striped>
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader>File</Table.ColumnHeader>
            <Table.ColumnHeader>Size</Table.ColumnHeader>
            <Table.ColumnHeader>Uploaded</Table.ColumnHeader>
            <Table.ColumnHeader>Actions</Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {files.map((file) => (
            <Table.Row key={file.file_id}>
              <Table.Cell>
                <HStack spacing={3}>
                  <Text fontSize="lg">{getFileIcon(file.original_name)}</Text>
                  <VStack align="start" spacing={0}>
                    <Text fontWeight="medium" fontSize="sm" color="gray.600">
                      {file.original_name}
                    </Text>
                    <Text fontSize="xs" color="gray.500">
                      {file.file_name}
                    </Text>
                  </VStack>
                </HStack>
              </Table.Cell>
              <Table.Cell>
                <Badge colorScheme="blue" variant="subtle">
                  {formatFileSize(file.file_size)}
                </Badge>
              </Table.Cell>
              <Table.Cell>
                <Text fontSize="sm" color="gray.600">
                  {formatDate(file.created_at)}
                </Text>
              </Table.Cell>
              <Table.Cell>
                <HStack spacing={1}>
                  <IconButton
                    size="sm"
                    aria-label="Download file"
                    onClick={() => {
                      // TODO: Implement download functionality
                      alert("Download functionality not implemented yet");
                    }}
                  >
                    <FiDownload />
                  </IconButton>
                  <IconButton
                    size="sm"
                    aria-label="Delete file"
                    onClick={() => handleDeleteFile(file.file_id)}
                  >
                    <FiTrash2 />
                  </IconButton>
                </HStack>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
    </Box>
  );
};

export default FilesList;

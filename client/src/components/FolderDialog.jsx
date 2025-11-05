import { API_URL } from "../config";
import {
  Button,
  CloseButton,
  Dialog,
  Input,
  Portal,
  VStack,
  HStack,
  Text,
  Box,
  IconButton,
  InputGroup,
  Alert,
  Spinner,
  Flex,
  Badge,
  Icon,
  Checkbox,
  Collapsible,
} from "@chakra-ui/react";
import { FiFolder, FiPlus, FiX, FiUpload, FiTrash2 } from "react-icons/fi";
import { useState, useEffect, useRef } from "react";

const FolderDialog = ({
  showFolderDialog,
  setShowFolderDialog,
  selectedFolders = [],
  setSelectedFolders,
}) => {
  console.log("FolderDialog props:", {
    showFolderDialog,
    selectedFolders,
    setSelectedFolders,
  });
  const [folders, setFolders] = useState([]);
  const [newFolderName, setNewFolderName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [uploadingFiles, setUploadingFiles] = useState({});
  const [folderFiles, setFolderFiles] = useState({});
  const [expandedFolder, setExpandedFolder] = useState(null);
  const fileInputRef = useRef(null);

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

  // Load folders on component mount
  useEffect(() => {
    if (showFolderDialog && user_id) {
      loadFolders();
    }
  }, [showFolderDialog, user_id]);

  const loadFolders = async () => {
    try {
      const response = await fetch(`${API_URL}/api/folders/${user_id}`, {
        method: "GET",
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        setFolders(data.folders || []);
      }
    } catch (error) {
      console.error("Error loading folders:", error);
    }
  };

  const createFolder = async () => {
    if (!newFolderName.trim() || !user_id) return;

    setIsCreating(true);
    try {
      const response = await fetch(`${API_URL}/api/folders/${user_id}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          folder_name: newFolderName.trim(),
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setFolders((prev) => [...prev, data.folder]);
        setNewFolderName("");
        alert("Folder created successfully!");
      } else {
        const errorData = await response.json();
        alert(`Error: ${errorData.error}`);
      }
    } catch (error) {
      alert(`Error creating folder: ${error.message}`);
    } finally {
      setIsCreating(false);
    }
  };

  const deleteFolder = async (folderId) => {
    if (
      !confirm(
        "Are you sure you want to delete this folder? This will also delete all files in it."
      )
    ) {
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:5001/api/folders/${user_id}/${folderId}`,
        {
          method: "DELETE",
          credentials: "include",
        }
      );

      if (response.ok) {
        setFolders((prev) =>
          prev.filter((folder) => folder.folder_id !== folderId)
        );
        if (selectedFolder === folderId) {
          setSelectedFolder(null);
        }
        alert("Folder deleted successfully!");
      } else {
        const errorData = await response.json();
        alert(`Error: ${errorData.error}`);
      }
    } catch (error) {
      alert(`Error deleting folder: ${error.message}`);
    }
  };

  const handleFileUpload = async (event, folderId) => {
    const files = event.target.files;
    if (!files || files.length === 0 || !folderId) return;

    if (!user_id) {
      alert("Please log in to upload files");
      return;
    }

    setIsUploading(true);
    setUploadingFiles({ ...uploadingFiles, [folderId]: true });

    try {
      const formData = new FormData();
      Array.from(files).forEach((file, index) => {
        formData.append(`file_${index}`, file);
      });
      formData.append("folder_id", folderId);

      const response = await fetch(`${API_URL}/api/file/upload/${user_id}`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (response.ok) {
        alert("Files uploaded successfully!");
        // Refresh folders to update file counts
        loadFolders();
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || "Upload failed");
      }
    } catch (error) {
      alert(`Upload failed: ${error.message}`);
    } finally {
      setIsUploading(false);
      setUploadingFiles({ ...uploadingFiles, [folderId]: false });
      // Reset file input
      const fileInput = document.getElementById(`file-upload-${folderId}`);
      if (fileInput) {
        fileInput.value = "";
      }
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !isCreating) {
      createFolder();
    }
  };

  // Handle folder selection for multi-select
  const handleFolderSelection = (folderId, isSelected) => {
    console.log("handleFolderSelection called with:", {
      folderId,
      isSelected,
      setSelectedFolders,
    });
    if (!setSelectedFolders || typeof setSelectedFolders !== "function") {
      console.error(
        "setSelectedFolders is not defined or not a function!",
        setSelectedFolders
      );
      return;
    }
    if (isSelected) {
      setSelectedFolders((prev) => [...(prev || []), folderId]);
    } else {
      setSelectedFolders((prev) =>
        (prev || []).filter((id) => id !== folderId)
      );
    }
  };

  // Remove folder from selection
  const removeSelectedFolder = (folderId) => {
    if (!setSelectedFolders || typeof setSelectedFolders !== "function") {
      console.error(
        "setSelectedFolders is not defined or not a function!",
        setSelectedFolders
      );
      return;
    }
    setSelectedFolders((prev) => (prev || []).filter((id) => id !== folderId));
  };

  // Load files for a specific folder
  const loadFolderFiles = async (folderId) => {
    if (!user_id) return;

    try {
      const response = await fetch(
        `http://localhost:5001/api/folders/${user_id}/${folderId}/files`,
        {
          method: "GET",
          credentials: "include",
        }
      );

      if (response.ok) {
        const data = await response.json();
        console.log("Files loaded for folder", folderId, ":", data);
        setFolderFiles((prev) => ({ ...prev, [folderId]: data.files || [] }));
      } else {
        console.error(
          "Failed to load files:",
          response.status,
          response.statusText
        );
      }
    } catch (error) {
      console.error("Error loading folder files:", error);
    }
  };

  // Toggle folder expansion
  const toggleFolderExpansion = (folderId) => {
    if (expandedFolder === folderId) {
      setExpandedFolder(null);
    } else {
      setExpandedFolder(folderId);
      loadFolderFiles(folderId);
    }
  };

  // Get context from selected folders

  return (
    <Dialog.Root
      size="cover"
      placement="center"
      motionPreset="scale"
      open={showFolderDialog}
      onOpenChange={(e) => setShowFolderDialog(e.open)}
    >
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content maxWidth="90vw" maxHeight="90vh" width="full">
            <Dialog.Header borderBottom="1px solid" borderColor="gray.200">
              <HStack justifyContent="space-between" width="full">
                <Dialog.Title fontSize="xl" fontWeight="semibold">
                  📁 Smart Folders
                </Dialog.Title>
                <Dialog.CloseTrigger asChild>
                  <IconButton
                    size="sm"
                    aria-label="Close dialog"
                    onClick={() => setShowFolderDialog(false)}
                  >
                    <FiX />
                  </IconButton>
                </Dialog.CloseTrigger>
              </HStack>
            </Dialog.Header>

            <Dialog.Body padding={6}>
              <VStack gap={6} alignItems="stretch">
                {/* Create Folder Section */}
                <Box>
                  <Text fontSize="md" fontWeight="medium" marginBottom={3}>
                    Create New Folder
                  </Text>
                  <HStack gap={3}>
                    <InputGroup
                      endElement={
                        <Button
                          size="sm"
                          colorPalette="blue"
                          onClick={createFolder}
                          loading={isCreating}
                          loadingText="Creating..."
                          disabled={!newFolderName.trim() || isCreating}
                        >
                          <Icon>
                            <FiPlus />
                          </Icon>
                          Create
                        </Button>
                      }
                    >
                      <Input
                        placeholder="Enter folder name..."
                        value={newFolderName}
                        onChange={(e) => setNewFolderName(e.target.value)}
                        onKeyPress={handleKeyPress}
                        disabled={isCreating}
                        color="black"
                        backgroundColor="white"
                        borderColor="gray.300"
                        _placeholder={{ color: "gray.500" }}
                        _focus={{
                          borderColor: "blue.500",
                          boxShadow: "0 0 0 1px blue.500",
                        }}
                      />
                    </InputGroup>
                  </HStack>
                </Box>

                {/* Selected Folders Badges */}
                {selectedFolders && selectedFolders.length > 0 && (
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" marginBottom={2}>
                      Selected Smart Folders:
                    </Text>
                    <HStack gap={2} wrap="wrap">
                      {selectedFolders.map((folderId) => {
                        const folder = folders.find(
                          (f) => f.folder_id === folderId
                        );
                        return (
                          <Badge
                            key={folderId}
                            colorPalette="blue"
                            size="sm"
                            padding={2}
                            borderRadius="md"
                          >
                            <HStack gap={1}>
                              <Text fontSize="xs">{folder?.folder_name}</Text>
                              <IconButton
                                size="xs"
                                variant="ghost"
                                onClick={() => removeSelectedFolder(folderId)}
                              >
                                <FiX size={12} />
                              </IconButton>
                            </HStack>
                          </Badge>
                        );
                      })}
                    </HStack>
                  </Box>
                )}

                {/* Folders List Section */}
                <Box>
                  <Text fontSize="md" fontWeight="medium" marginBottom={3}>
                    Your Smart Folders
                  </Text>
                  {folders.length === 0 ? (
                    <Alert.Root status="info">
                      ℹ️ No folders created yet. Create your first folder above!
                    </Alert.Root>
                  ) : (
                    <VStack gap={2} alignItems="stretch">
                      {folders.map((folder) => (
                        <Box
                          key={folder.folder_id}
                          padding={4}
                          border="1px solid"
                          borderColor="gray.200"
                          rounded="md"
                          backgroundColor="white"
                          _hover={{ bg: "gray.50" }}
                        >
                          <Flex
                            justifyContent="space-between"
                            alignItems="center"
                          >
                            <HStack gap={3}>
                              <Checkbox.Root
                                checked={
                                  selectedFolders &&
                                  selectedFolders.includes(folder.folder_id)
                                }
                                onCheckedChange={(e) =>
                                  handleFolderSelection(
                                    folder.folder_id,
                                    !!e.checked
                                  )
                                }
                              >
                                <Checkbox.HiddenInput />
                                <Checkbox.Control />
                              </Checkbox.Root>
                              <Box
                                cursor="pointer"
                                onClick={() =>
                                  toggleFolderExpansion(folder.folder_id)
                                }
                                flex="1"
                              >
                                <HStack gap={3}>
                                  <FiFolder size={20} color="#3182ce" />
                                  <VStack alignItems="start" gap={0}>
                                    <Text fontWeight="medium">
                                      {folder.folder_name}
                                    </Text>
                                    <Text fontSize="sm" color="gray.500">
                                      Created:{" "}
                                      {new Date(
                                        folder.created_at
                                      ).toLocaleDateString()}
                                    </Text>
                                    <HStack gap={2}>
                                      <Badge colorPalette="blue" size="sm">
                                        {folder.file_count || 0} files
                                      </Badge>
                                      <Badge colorPalette="green" size="sm">
                                        Vector DB: {folder.vector_db_name}
                                      </Badge>
                                    </HStack>
                                  </VStack>
                                </HStack>
                              </Box>
                            </HStack>
                            <HStack gap={2}>
                              <input
                                ref={fileInputRef}
                                type="file"
                                multiple
                                accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.gif,.xls,.xlsx,.csv"
                                onChange={(e) =>
                                  handleFileUpload(e, folder.folder_id)
                                }
                                style={{ display: "none" }}
                                id={`file-upload-${folder.folder_id}`}
                              />
                              <Button
                                size="sm"
                                colorPalette="green"
                                variant="outline"
                                loading={uploadingFiles[folder.folder_id]}
                                loadingText="Uploading..."
                                onClick={() =>
                                  document
                                    .getElementById(
                                      `file-upload-${folder.folder_id}`
                                    )
                                    .click()
                                }
                              >
                                <Icon>
                                  <FiUpload />
                                </Icon>
                                Upload
                              </Button>
                              <Button
                                size="sm"
                                colorPalette="red"
                                variant="outline"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  deleteFolder(folder.folder_id);
                                }}
                              >
                                <Icon>
                                  <FiTrash2 />
                                </Icon>
                                Delete
                              </Button>
                            </HStack>
                          </Flex>

                          {/* Collapsible Files Section */}
                          <Collapsible.Root
                            open={expandedFolder === folder.folder_id}
                          >
                            <Collapsible.Content>
                              <Box
                                marginTop={3}
                                paddingTop={3}
                                borderTop="1px solid"
                                borderColor="gray.200"
                              >
                                <Text
                                  fontSize="sm"
                                  fontWeight="medium"
                                  marginBottom={2}
                                >
                                  Files in this folder:
                                </Text>
                                {(() => {
                                  const files = folderFiles[folder.folder_id];
                                  console.log(
                                    "Files for folder",
                                    folder.folder_id,
                                    ":",
                                    files
                                  );

                                  if (files && files.length > 0) {
                                    console.log(
                                      "First file structure:",
                                      files[0]
                                    );
                                  }

                                  if (files === undefined) {
                                    return (
                                      <Text
                                        fontSize="sm"
                                        color="gray.600"
                                        fontWeight="medium"
                                      >
                                        Loading files...
                                      </Text>
                                    );
                                  }

                                  if (files.length === 0) {
                                    return (
                                      <Text
                                        fontSize="sm"
                                        color="gray.600"
                                        fontWeight="medium"
                                      >
                                        No files in this folder yet.
                                      </Text>
                                    );
                                  }

                                  return (
                                    <VStack gap={1} alignItems="stretch">
                                      {files.map((file, index) => (
                                        <Box
                                          key={file.file_id || index}
                                          padding={2}
                                          backgroundColor="gray.50"
                                          rounded="sm"
                                          fontSize="sm"
                                          border="1px solid"
                                          borderColor="gray.200"
                                        >
                                          <Text
                                            fontWeight="medium"
                                            color="black"
                                          >
                                            {file.original_name ||
                                              file.filename ||
                                              file.name ||
                                              "Unknown file"}
                                          </Text>
                                          <Text fontSize="xs" color="gray.600">
                                            Uploaded:{" "}
                                            {file.uploaded_at
                                              ? new Date(
                                                  file.uploaded_at
                                                ).toLocaleDateString()
                                              : "Unknown date"}
                                          </Text>
                                          <Text fontSize="xs" color="gray.500">
                                            Type: {file.file_type || "Unknown"}{" "}
                                            | Size:{" "}
                                            {file.file_size
                                              ? `${Math.round(
                                                  file.file_size / 1024
                                                )}KB`
                                              : "Unknown"}
                                          </Text>
                                        </Box>
                                      ))}
                                    </VStack>
                                  );
                                })()}
                              </Box>
                            </Collapsible.Content>
                          </Collapsible.Root>
                        </Box>
                      ))}
                    </VStack>
                  )}
                </Box>

                {/* Instructions */}
                <Box padding={4} backgroundColor="gray.50" rounded="md">
                  <Text fontSize="sm" color="gray.600">
                    <strong>Instructions:</strong>
                    <br />
                    • Click on a folder to select it and upload files
                    <br />
                    • Each folder has its own separate vector database
                    <br />
                    • Files uploaded to a folder will be indexed in that
                    folder's vector DB
                    <br />• Only files can be uploaded (no subfolders)
                  </Text>
                </Box>
              </VStack>
            </Dialog.Body>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
};

export default FolderDialog;

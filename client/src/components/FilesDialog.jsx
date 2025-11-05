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
} from "@chakra-ui/react";
import FilesList from "./FilesList";
import { FiUpload, FiX } from "react-icons/fi";
import { useState, useRef } from "react";

const FilesDialog = ({ showFilesDialog, setShowFilesDialog }) => {
  const [uploading, setUploading] = useState(false);
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
  const handleFileUpload = async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    if (!user_id) {
      alert("Please log in to upload files");
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      Array.from(files).forEach((file, index) => {
        formData.append(`file_${index}`, file);
      });

      const response = await fetch(`${API_URL}/api/file/upload/${user_id}`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (response.ok) {
        alert("Files uploaded successfully!");
        // Refresh the files list
        window.dispatchEvent(new CustomEvent("filesUpdated"));
      } else {
        throw new Error("Upload failed");
      }
    } catch (error) {
      alert(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <Dialog.Root
      size="cover"
      placement="center"
      motionPreset="scale"
      open={showFilesDialog}
    >
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content maxW="90vw" maxH="90vh" w="full">
            <Dialog.Header borderBottom="1px solid" borderColor="gray.200">
              <HStack justify="space-between" w="full">
                <Dialog.Title fontSize="xl" fontWeight="semibold">
                  📁 Files Manager
                </Dialog.Title>
                <Dialog.CloseTrigger asChild>
                  <IconButton
                    size="sm"
                    aria-label="Close dialog"
                    onClick={() => setShowFilesDialog(false)}
                  >
                    <FiX />
                  </IconButton>
                </Dialog.CloseTrigger>
              </HStack>
            </Dialog.Header>

            <Dialog.Body p={6}>
              <VStack spacing={6} align="stretch">
                {/* Upload Section */}
                <Box>
                  <Text fontSize="md" fontWeight="medium" mb={3}>
                    Upload New Files
                  </Text>
                  <HStack spacing={3}>
                    <Input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.gif,.xls,.xlsx,.csv"
                      onChange={handleFileUpload}
                      display="none"
                      id="file-upload"
                    />
                    <Button
                      as="label"
                      htmlFor="file-upload"
                      leftIcon={<FiUpload />}
                      colorScheme="blue"
                      variant="outline"
                      isLoading={uploading}
                      loadingText="Uploading..."
                      cursor="pointer"
                    >
                      Choose Files
                    </Button>
                    <Text fontSize="sm" color="gray.500">
                      Max 5 files, 10MB each
                    </Text>
                  </HStack>
                </Box>

                {/* Files List Section */}
                <Box>
                  <Text fontSize="md" fontWeight="medium" mb={3}>
                    Your Files
                  </Text>
                  <FilesList />
                </Box>
              </VStack>
            </Dialog.Body>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
};
export default FilesDialog;

import { Textarea } from "@chakra-ui/react";
const ChatInputArea = () => {
  return (
    <Textarea
      placeholder="Type your message here..."
      autoresize
      bg="gray.800"
    />
  );
};
export default ChatInputArea;

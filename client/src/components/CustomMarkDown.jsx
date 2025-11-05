import React, { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import { Box, Text, Code, Link, IconButton } from "@chakra-ui/react";
import "highlight.js/styles/atom-one-dark.css"; // Syntax highlighting theme
import "katex/dist/katex.min.css"; // KaTeX CSS for math rendering
import "./custom-syntax-highlighting.css"; // Custom syntax highlighting styles
import { RxCopy } from "react-icons/rx";

const CustomMarkDown = memo(
  ({ content, applyMarkDown, codeBlockMarginY = 4 }) => {
    return (
      <Box
        width="100%"
        sx={{
          fontSize: { base: "sm", md: "md" },
          "& > * + *": {
            mt: 1,
          },
        }}
      >
        {applyMarkDown && (
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeHighlight, rehypeKatex]}
            components={{
              // Paragraph text
              p: ({ children, ...props }) => (
                <Text
                  fontSize={{ base: "sm", md: "md" }}
                  color="chakra-body-text"
                  _selection={{ bg: "chakra-subtle-bg" }}
                  {...props}
                >
                  {children}
                </Text>
              ),
              // strong: ({ children, ...props }) => (
              //   <Text as="strong" fontWeight="bold" {...props} fontSize="md">
              //     {children}
              //   </Text>
              // ),

              // Links
              a: ({ href, children, ...props }) => (
                <Link
                  href={href}
                  fontSize={{ base: "sm", md: "md" }}
                  color="blue.400"
                  target="_blank"
                  rel="noopener noreferrer"
                  wordBreak="break-all"
                  overflowWrap="break-word"
                  display="inline-block"
                  maxWidth="100%"
                  _hover={{
                    textDecoration: "none",
                  }}
                  _focus={{
                    outline: "none",
                  }}
                  {...props}
                >
                  {children}
                </Link>
              ),

              // Code blocks and inline code
              code: ({ inline, className, children, ...props }) => {
                const match = /language-(\w+)/.exec(className || "");

                return !inline && match ? (
                  // Code block
                  <Box
                    width="100%"
                    my={codeBlockMarginY}
                    borderRadius="md"
                    overflow="hidden"
                    {...props}
                  >
                    <Box
                      display="flex"
                      justifyContent="space-between"
                      alignItems="center"
                      px={2}
                      py={2}
                      width="100%"
                      borderBottom="0.5px solid"
                      borderColor="gray.700"
                      style={{
                        backgroundColor: "black",
                      }}
                    >
                      <Text fontSize="xs" fontWeight="medium" color="white">
                        {match[1]}
                      </Text>
                    </Box>
                    <Box
                      as="pre"
                      bg="black"
                      overflowX="auto"
                      fontSize={{ base: "xs", md: "sm" }}
                      width="100%"
                      whiteSpace="pre-wrap"
                    >
                      <code
                        className={className}
                        style={{
                          backgroundColor: "black",
                        }}
                      >
                        {children}
                      </code>
                    </Box>
                  </Box>
                ) : (
                  // Inline code
                  <Code
                    fontSize={{ base: "xs", md: "sm" }}
                    px={2}
                    py={0.5}
                    bg="gray.700"
                    color="gray.100"
                    borderRadius="sm"
                    variant="outline"
                    {...props}
                  >
                    {children}
                  </Code>
                );
              },

              // Headings
              h1: ({ children, ...props }) => (
                <Text
                  as="h1"
                  fontSize={{ base: "1xl", md: "3xl" }}
                  fontWeight="bold"
                  color="chakra-body-text"
                  mt={2}
                  mb={1}
                  {...props}
                >
                  {children}
                </Text>
              ),
              h2: ({ children, ...props }) => (
                <Text
                  as="h2"
                  fontSize={{ base: "md", md: "lg" }}
                  fontWeight="semibold"
                  color="chakra-body-text"
                  mt={1.5}
                  mb={0.5}
                  {...props}
                >
                  {children}
                </Text>
              ),
              h3: ({ children, ...props }) => (
                <Text
                  as="h3"
                  fontSize={{ base: "lg", md: "xl" }}
                  fontWeight="medium"
                  color="chakra-body-text"
                  mt={1}
                  mb={0.5}
                  {...props}
                >
                  {children}
                </Text>
              ),
              h4: ({ children, ...props }) => (
                <Text
                  as="h4"
                  fontSize={{ base: "md", md: "lg" }}
                  fontWeight="medium"
                  color="chakra-body-text"
                  mt={1}
                  mb={0.5}
                  {...props}
                >
                  {children}
                </Text>
              ),

              // Lists
              ul: ({ children, ...props }) => (
                <Box
                  as="ul"
                  pl={4}
                  listStyleType="disc"
                  fontSize="sm"
                  color="chakra-body-text"
                  my={1}
                  {...props}
                >
                  {children}
                </Box>
              ),
              ol: ({ children, ...props }) => (
                <Box
                  as="ol"
                  pl={4}
                  listStyleType="decimal"
                  fontSize={{ base: "sm", md: "md" }}
                  color="chakra-body-text"
                  my={1}
                  {...props}
                >
                  {children}
                </Box>
              ),
              li: ({ children, ...props }) => (
                <Text
                  as="li"
                  fontSize={{ base: "sm", md: "md" }}
                  color="chakra-body-text"
                  mb={0.5}
                  {...props}
                >
                  {children}
                </Text>
              ),

              // Blockquote
              blockquote: ({ children, ...props }) => (
                <Box
                  as="blockquote"
                  borderLeft="4px solid"
                  borderColor="blue.400"
                  pl={4}
                  py={2}
                  my={4}
                  fontStyle="italic"
                  color="chakra-body-text"
                  bg="chakra-subtle-bg"
                  borderRadius="md"
                  {...props}
                >
                  {children}
                </Box>
              ),

              // Horizontal Rule
              hr: (props) => (
                <Box
                  as="hr"
                  border="none"
                  height="1px"
                  bg="gray.700"
                  my={4}
                  {...props}
                />
              ),

              // Table
              table: ({ children, ...props }) => (
                <Box
                  width="100%"
                  my={4}
                  overflow="auto"
                  sx={{
                    borderCollapse: "collapse",
                    display: "block",
                  }}
                  {...props}
                >
                  <Box as="table" width="100%" pl={0} {...props}>
                    {children}
                  </Box>
                </Box>
              ),
              thead: ({ children, ...props }) => (
                <Box as="thead" {...props}>
                  {children}
                </Box>
              ),
              tbody: ({ children, ...props }) => (
                <Box as="tbody" {...props}>
                  {children}
                </Box>
              ),
              tr: ({ children, ...props }) => (
                <Box as="tr" {...props}>
                  {children}
                </Box>
              ),
              th: ({ children, ...props }) => (
                <Text
                  as="th"
                  px={2}
                  py={2}
                  fontSize="sm"
                  fontWeight="semibold"
                  color="chakra-body-text"
                  borderBottom="1px solid"
                  borderColor="gray.600"
                  textAlign="left"
                  {...props}
                >
                  {children}
                </Text>
              ),
              td: ({ children, ...props }) => (
                <Text
                  as="td"
                  px={2}
                  py={2}
                  fontSize="sm"
                  color="chakra-body-text"
                  borderBottom="1px solid"
                  borderColor="gray.700"
                  {...props}
                >
                  {children}
                </Text>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        )}
        {!applyMarkDown && <Text whiteSpace="pre-wrap">{content}</Text>}
      </Box>
    );
  }
);

export default CustomMarkDown;

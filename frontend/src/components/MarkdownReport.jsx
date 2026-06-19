import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Thin wrapper so react-markdown + remark-gfm (~heavy) can be code-split via React.lazy
// and only loaded when a Deep Research report actually renders.
export default function MarkdownReport({ children, components }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {children}
    </ReactMarkdown>
  );
}

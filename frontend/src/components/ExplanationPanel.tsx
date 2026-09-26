import type { Explanation } from "../api/types";

export function ExplanationPanel({ explanation }: { explanation: Explanation }) {
  return (
    <div className="explanation" data-testid="explanation">
      <h3>The full answer</h3>
      <Prose text={explanation.answer} />

      {explanation.points.length > 0 && (
        <>
          <h3>Point by point</h3>
          <dl>
            {explanation.points.map(({ point, detail }) => (
              <div key={point}>
                <dt>
                  <Inline text={point} />
                </dt>
                <dd>
                  <Inline text={detail} />
                </dd>
              </div>
            ))}
          </dl>
        </>
      )}

      {explanation.pitfalls.length > 0 && (
        <>
          <h3>Common pitfalls</h3>
          <ul>
            {explanation.pitfalls.map((pitfall) => (
              <li key={pitfall}>
                <Inline text={pitfall} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

// The answer arrives as one string of markdown-ish prose: paragraphs split by
// blank lines, and — since the model is asked for a concrete example — often a
// fenced code block and backticked identifiers, which read as noise unrendered.
function Prose({ text }: { text: string }) {
  return (
    <>
      {blocks(text).map((block, index) =>
        block.code ? (
          <pre key={index}>
            <code>{block.text}</code>
          </pre>
        ) : (
          <p key={index}>
            <Inline text={block.text} />
          </p>
        ),
      )}
    </>
  );
}

function Inline({ text }: { text: string }) {
  return (
    <>
      {text.split(/`([^`]+)`/).map((part, index) =>
        // The split alternates plain text and what sat between the backticks.
        index % 2 === 0 ? part : <code key={index}>{part}</code>,
      )}
    </>
  );
}

type Block = { code: boolean; text: string };

const FENCED = /```[\w]*\r?\n?([\s\S]*?)```/g;

function blocks(text: string): Block[] {
  const found: Block[] = [];
  let read = 0;

  for (const fence of text.matchAll(FENCED)) {
    found.push(...paragraphs(text.slice(read, fence.index)));
    found.push({ code: true, text: fence[1].replace(/\s+$/, "") });
    read = fence.index + fence[0].length;
  }
  found.push(...paragraphs(text.slice(read)));

  return found;
}

function paragraphs(text: string): Block[] {
  return text
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter((part) => part !== "")
    .map((part) => ({ code: false, text: part }));
}

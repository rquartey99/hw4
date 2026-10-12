import { Fragment, type ReactNode } from 'react'

// Renders the small Markdown subset the assistant uses (**bold**, *italic*, `-` bullet lists, paragraphs)
// as React elements. No HTML is injected, so model output can't add scripts or links to the page.

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) return <strong key={i}>{part.slice(2, -2)}</strong>
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) return <em key={i}>{part.slice(1, -1)}</em>
    return <Fragment key={i}>{part}</Fragment>
  })
}

export default function ChatMarkdown({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  let paragraph: string[] = []

  const flushBullets = () => {
    if (bullets.length) {
      blocks.push(
        <ul key={blocks.length}>
          {bullets.map((b, i) => (
            <li key={i}>{inline(b)}</li>
          ))}
        </ul>,
      )
      bullets = []
    }
  }
  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push(<p key={blocks.length}>{inline(paragraph.join(' '))}</p>)
      paragraph = []
    }
  }

  for (const raw of text.split('\n')) {
    const line = raw.trim()
    const bullet = line.match(/^[-*•]\s+(.*)$/)
    if (bullet) {
      flushParagraph()
      bullets.push(bullet[1])
    } else if (line === '') {
      flushParagraph()
      flushBullets()
    } else {
      flushBullets()
      paragraph.push(line.replace(/^#+\s*/, ''))
    }
  }
  flushParagraph()
  flushBullets()

  return <>{blocks}</>
}

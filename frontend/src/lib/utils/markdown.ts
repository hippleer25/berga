import { unified } from 'unified'
import type { Root } from 'hast'
import { visit } from 'unist-util-visit'
import remarkParse from 'remark-parse'
import remarkGfm from 'remark-gfm'
import remarkRehype from 'remark-rehype'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import rehypeStringify from 'rehype-stringify'

const sanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    a: [...(defaultSchema.attributes?.a ?? []), 'target', 'rel'],
  },
}

function rehypeExternalLinks() {
  return (tree: Root) => {
    visit(tree, 'element', (node) => {
      if (node.tagName === 'a' && node.properties?.href) {
        node.properties = {
          ...node.properties,
          target: '_blank',
          rel: 'noopener noreferrer',
        }
      }
    })
  }
}

function preprocessWikilinks(md: string): string {
  return md.replace(/\[\[([^\]]+)\]\]/g, (_m, inner: string) => {
    const sep = inner.lastIndexOf('^^')
    if (sep >= 0) {
      const text = inner.slice(0, sep).trim()
      const url = inner.slice(sep + 2).trim()
      if (url) return `[${text || url}](${url})`
    }
    const trimmed = inner.trim()
    if (/^https?:\/\//i.test(trimmed)) {
      return `[${trimmed}](${trimmed})`
    }
    if (/^[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}/.test(trimmed)) {
      return `[${trimmed}](https://${trimmed})`
    }
    return `[${trimmed}](${trimmed})`
  })
}

let processor: any = null

function getProcessor() {
  if (!processor) {
    processor = unified()
      .use(remarkParse)
      .use(remarkGfm)
      .use(remarkRehype)
      .use(rehypeExternalLinks)
      .use(rehypeSanitize, sanitizeSchema)
      .use(rehypeStringify)
  }
  return processor
}

export function renderMarkdown(content: string): string {
  const processed = preprocessWikilinks(content)
  try {
    const file = getProcessor().processSync(processed)
    return String(file)
  } catch {
    return `<p>${processed}</p>`
  }
}

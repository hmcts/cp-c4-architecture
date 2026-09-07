import { defineConfig } from 'likec4/config'

export default defineConfig({
  name: 'common-platform',
  title: 'Common Platform',
  exclude: [
    'node_modules/**'
  ],
  generators: {
    /**
     * Generates CSV file with relationships to the 
     * 
     */
    'relationships-csv': async ({ likec4model, ctx }) => {
      const lines = [] as string[]
      for (const r of likec4model.relationships()) {
        const loc = ctx.locate(r)
        lines.push(
          [
            `${r.source.id} -> ${r.target.id}`,
            `${r.title || ''}`,
            `${loc.relativePath} [Ln ${loc.range.start.line}, Col ${loc.range.start.character}]`,
          ]
          .map(s => `"${s.replace('"', '\\"')}"`)
          .join(',')
        )
      }
      // If no relationships found, abort
      if (lines.length === 0) {
        return ctx.abort('No relationships found')
      }
      // Write to file (relative to project root)
      await ctx.write({
        path: 'relationships.csv',
        content: 'relationship,title,location\n' + lines.join('\n')
      })
    },
    /**
     * Generates JSON mapping every GitHub repository link in the model to the
     * product (or shared component), subdomain and product area that owns it.
     * Consumed by scripts/delivery_metrics.py.
     */
    'repo-teams-json': async ({ likec4model, ctx }) => {
      // A repo's owning "product" is the nearest ancestor of either kind.
      const productKinds = ['product', 'shared-component']

      // The seven product areas the programme reports against, keyed by subdomain id.
      // There is deliberately no per-product override: an area is a subdomain, and
      // a single product promoted to one (cpp-ui-home was, as "Common Platform User
      // Interface") reports a five-ticket area beside a hundred-ticket one.
      const areaOfSubdomain: Record<string, string> = {
        'case-administration-subdomain': 'Case Administration',
        'case-ingestion-subdomain': 'Case Ingestion',
        'court-hearings-subdomain': 'Court Hearing',
        'dlrm-subdomain': 'DLRM',
        'opami-subdomain': 'Management Information System',
        'scheduling-and-listing-subdomain': 'Scheduling & Listing System',
        'shared-components-subdomain': 'Platform Engineering',
      }

      const rows = [] as any[]
      for (const element of likec4model.elements()) {
        const raw = (element as any).$element ?? {}
        const links = (raw.links ?? (element as any).links ?? []) as any[]
        const repos = links
          .map(l => /github\.com\/([^/\s]+)\/([A-Za-z0-9._-]+)/.exec(String(l.url ?? l)))
          .filter(Boolean)
          .map(m => ({ owner: m![1], repo: m![2] }))
        if (repos.length === 0) continue

        // Walk up to the owning product/shared-component and its subdomain.
        const ancestors = [element, ...Array.from(element.ancestors() as any)]
        const product = ancestors.find((a: any) => productKinds.includes(a.kind))
        const subdomain = ancestors.find((a: any) => a.kind === 'subdomain')
        if (!product || !subdomain) continue

        const productId = String(product.id).split('.').pop()!
        const subdomainId = String(subdomain.id).split('.').pop()!
        for (const { owner, repo } of repos) {
          rows.push({
            owner,
            repo,
            component: element.title,
            componentKind: element.kind,
            product: productId,
            productTitle: product.title,
            productKind: product.kind,
            subdomain: subdomainId,
            subdomainTitle: subdomain.title,
            area: areaOfSubdomain[subdomainId] ?? subdomain.title,
          })
        }
      }

      if (rows.length === 0) {
        return ctx.abort('No repository links found in the model')
      }

      rows.sort((a, b) =>
        a.area.localeCompare(b.area) ||
        a.productTitle.localeCompare(b.productTitle) ||
        a.repo.localeCompare(b.repo))

      await ctx.write({
        path: 'repo-teams.json',
        content: JSON.stringify({ generatedFrom: 'likec4 model', repos: rows }, null, 2) + '\n'
      })
    },

    /**
     * Generates CSV file with containers grouped by product
     */
    'product-components-csv': async ({ likec4model, ctx }) => {
      interface Row {
        subdomain: string
        product: string
        productType: string
        component: string
        componentType: string
        technology: string
      }

      // Helper function to format type strings: remove hyphens and capitalize each word
      const formatType = (type: string): string => {
        return type
          .split('-')
          .map(word => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ')
      }

      // Included product kinds
      const productKinds = ['product', 'shared-component']

      const productsWithComponents = new Set<string>()
      const products = new Map<string, { element: any, subdomain: any }>()
      const containerRows: Row[] = []
      const productRows: Row[] = []

      // Query all elements in a single loop
      const allElements = Array.from(likec4model.elements())

      for (const element of allElements) {
        // Extract hierarchy from ID
        const idParts = element.id.split('.')

        // Skip if not in expected hierarchy (need at least 3 parts)
        if (idParts.length < 3 || idParts[0] !== 'cp') continue

        // Collect all products for later processing
        if (idParts.length === 3 && productKinds.includes(element.kind)) {
          const subdomainId = `${idParts[0]}.${idParts[1]}`
          const subdomain = likec4model.element(subdomainId)
          if (subdomain) {
            products.set(element.id, { element, subdomain })
          }
          continue
        }

        // Handle containers
        if (idParts.length >= 4) {
          // Build parent IDs
          const subdomainId = `${idParts[0]}.${idParts[1]}`
          const productId = `${idParts[0]}.${idParts[1]}.${idParts[2]}`

          // Look up parent elements
          const subdomain = likec4model.element(subdomainId)
          const product = likec4model.element(productId)

          // Skip if parent is not a product or shared-component
          if (!subdomain || !product) continue
          if (!productKinds.includes(product.kind)) continue

          // Only include elements whose direct parent is a product or shared-component
          const parentId = idParts.slice(0, -1).join('.')
          const parent = likec4model.element(parentId)
          if (!parent || !productKinds.includes(parent.kind)) continue

          productsWithComponents.add(productId)

          containerRows.push({
            subdomain: subdomain.title,
            product: product.title,
            productType: formatType(product.kind),
            component: element.title,
            componentType: formatType(element.kind),
            technology: element.technology || ''
          })
        }
      }

      // Collect rows for products without components
      for (const [productId, { element, subdomain }] of products) {
        if (!productsWithComponents.has(productId)) {
          productRows.push({
            subdomain: subdomain.title,
            product: element.title,
            productType: formatType(element.kind),
            component: '',
            componentType: '',
            technology: ''
          })
        }
      }

      // Combine all rows
      const rows = [...containerRows, ...productRows]

      // Sort alphabetically: subdomain → product → component
      rows.sort((a, b) => {
        return a.subdomain.localeCompare(b.subdomain) ||
               a.product.localeCompare(b.product) ||
               a.component.localeCompare(b.component)
      })

      // Build CSV content
      const lines = rows.map(r =>
        [r.subdomain, r.product, r.productType,
         r.component, r.componentType, r.technology]
          .map(s => `"${String(s).replace(/"/g, '\\"')}"`)
          .join(',')
      )

      // Write to file (relative to project root)
      await ctx.write({
        path: 'product-components.csv',
        content: 'Subdomain,Product,Product Type,Component Name,Component Type,Technology\n' +
                 lines.join('\n')
      })
    }
  },
})

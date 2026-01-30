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

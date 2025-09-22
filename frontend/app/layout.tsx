export const metadata = {
  title: 'Memoria',
  description: 'Long-term memory for LLMs'
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}



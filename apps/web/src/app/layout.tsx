import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Calculadora de Ponto de Função",
  description: "IFPUG Function Point analysis powered by a local LLM."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <div className="min-h-screen">
            <header className="border-b">
              <div className="container flex h-14 items-center">
                <span className="font-semibold">Function Point Calculator</span>
              </div>
            </header>
            <main className="container py-8">{children}</main>
            <footer className="border-t">
              <div className="container py-4 text-xs text-muted-foreground">
                Local, no-auth analysis · Powered by Ollama
              </div>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}

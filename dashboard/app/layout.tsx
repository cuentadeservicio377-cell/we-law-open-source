import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Hermes We Law OS",
  description: "Despacho legal operativo controlado por Hermes",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <div className="app-shell">
          <Nav />
          <main className="shell">{children}</main>
        </div>
      </body>
    </html>
  );
}

import { Html, Head, Main, NextScript } from "next/document";

export default function Document() {
  return (
    <Html lang="es">
      <Head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <meta name="description" content="Athletics — plataforma premium para entrenadores y atletas." />
        <meta name="theme-color" content="#0b1220" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}

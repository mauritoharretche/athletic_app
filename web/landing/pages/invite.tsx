import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useMemo } from "react";

import styles from "@/styles/Invite.module.css";

const stores = [
  { name: "TestFlight / iOS", url: "https://testflight.apple.com/" },
  { name: "Expo Go / Android", url: "https://expo.dev/client" },
];

export default function InvitePage() {
  const router = useRouter();
  const email = useMemo(() => {
    if (!router.isReady) return "";
    const raw = Array.isArray(router.query.email) ? router.query.email[0] : router.query.email;
    return raw ?? "";
  }, [router]);

  return (
    <>
      <Head>
        <title>Invitación Athletics — Vincula tu cuenta</title>
      </Head>
      <main className={styles.wrapper}>
        <section className={styles.card}>
          <p className="pill">Invitación recibida</p>
          <h1>Vincula tu cuenta y comienza a entrenar.</h1>
          <p>
            Inicia sesión en la app móvil con el correo <strong>{email || "que recibiste en el correo"}</strong>{" "}
            y acepta la invitación desde la sección de alertas. Si aún no tienes la app, descárgala aquí:
          </p>
          <div className={styles.storeGrid}>
            {stores.map((store) => (
              <a key={store.name} href={store.url} target="_blank" rel="noreferrer" className={styles.storeCard}>
                {store.name}
              </a>
            ))}
          </div>
          <p className={styles.helpText}>
            ¿No puedes acceder? <Link href="mailto:support@athletics.app">Escríbenos</Link> y te ayudaremos.
          </p>
        </section>
      </main>
    </>
  );
}

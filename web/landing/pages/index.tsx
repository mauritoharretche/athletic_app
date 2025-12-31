import Head from "next/head";
import Link from "next/link";
import styles from "@/styles/Home.module.css";

const features = [
  {
    title: "Planes inteligentes",
    copy: "Duplica, ajusta y publica planes semanales en segundos con métricas claras.",
  },
  {
    title: "Agenda del atleta",
    copy: "Los atletas reciben recordatorios, registran sensaciones y comparten feedback en tiempo real.",
  },
  {
    title: "Alertas accionables",
    copy: "Detección automática de baja adherencia, sesiones pendientes y streaks pausados.",
  },
];

const steps = [
  "Crea tu cuenta como coach o atleta.",
  "Envía una invitación y vincula a tu equipo.",
  "Diseña planes, registra sesiones y comparte la progresión.",
];

export default function Home() {
  return (
    <>
      <Head>
        <title>Athletics — Plataforma moderna para entrenadores y atletas</title>
      </Head>
      <main className={styles.main}>
        <header className={styles.hero}>
          <div>
            <div className="pill">Entrenamiento de alto rendimiento</div>
            <h1>Controla tus planes y motiva a tus atletas desde cualquier lugar.</h1>
            <p>
              Athletics es la plataforma profesional para diseñar planes de pista, calle o trail, monitorear
              cumplimiento y ofrecer feedback personalizado con una experiencia moderna.
            </p>
            <div className={styles.actions}>
              <a
                className={styles.primaryButton}
                href="https://expo.dev/"
                target="_blank"
                rel="noreferrer"
              >
                Descargar App
              </a>
              <Link className={styles.secondaryButton} href="/invite">
                Tengo una invitación
              </Link>
            </div>
            <div className={styles.metrics}>
              <div>
                <span>+1200</span>
                <p>Planes creados</p>
              </div>
              <div>
                <span>93%</span>
                <p>Tasa de cumplimiento</p>
              </div>
              <div>
                <span>24/7</span>
                <p>Alertas inteligentes</p>
              </div>
            </div>
          </div>
          <div className={styles.deviceMock}>
            <div className={styles.cardGlass}>
              <p>Entrenamiento de hoy</p>
              <strong>Fartlek progresivo</strong>
              <small>45 min · RPE 7</small>
            </div>
            <div className={styles.cardGlassSecondary}>
              <p>Volumen semanal</p>
              <h3>58 km</h3>
              <small>+12% vs semana anterior</small>
            </div>
          </div>
        </header>

        <section className={styles.section}>
          <h2>Todo lo que necesitas para entrenar con claridad</h2>
          <div className={styles.featureGrid}>
            {features.map((feature) => (
              <article key={feature.title}>
                <h3>{feature.title}</h3>
                <p>{feature.copy}</p>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <h2>Cómo funciona</h2>
          <ol className={styles.timeline}>
            {steps.map((step, index) => (
              <li key={step}>
                <span>{index + 1}</span>
                <p>{step}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className={styles.section}>
          <div className={styles.ctaCard}>
            <div>
              <p className="pill">¿Listo para comenzar?</p>
              <h2>Conecta a tu equipo y desbloquea una experiencia premium.</h2>
              <p className={styles.ctaCopy}>
                Desde la app móvil podrás crear invitaciones, duplicar planes y recibir recordatorios
                automáticos por correo.
              </p>
            </div>
            <Link className={styles.primaryButton} href="/invite">
              Vincular invitación
            </Link>
          </div>
        </section>
      </main>
    </>
  );
}

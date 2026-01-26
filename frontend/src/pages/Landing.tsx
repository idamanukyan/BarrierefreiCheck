/**
 * Landing Page
 *
 * Public landing page visible to everyone without login.
 */

import React from 'react';
import { Link } from 'react-router-dom';

const Landing: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center">
              <span className="text-2xl font-bold text-blue-600">BarrierefreiCheck</span>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                to="/login"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium"
              >
                Anmelden
              </Link>
              <Link
                to="/register"
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Kostenlos starten
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-6">
            BFSG-Compliance in
            <span className="text-blue-600"> 5 Minuten</span>
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
            Prüfen Sie Ihre Website auf Barrierefreiheit nach WCAG 2.1 und BFSG.
            Erhalten Sie sofortige Ergebnisse mit konkreten Handlungsempfehlungen auf Deutsch.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link
              to="/register"
              className="bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors shadow-lg"
            >
              Jetzt kostenlos testen
            </Link>
            <Link
              to="/login"
              className="bg-white text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-gray-50 transition-colors border border-blue-200"
            >
              Anmelden
            </Link>
          </div>
        </div>
      </section>

      {/* BFSG Warning Banner */}
      <section className="bg-yellow-50 border-y border-yellow-200 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center gap-3">
            <svg className="h-6 w-6 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-yellow-800 font-medium">
              <strong>BFSG-Frist: 28. Juni 2025</strong> - Bis zu 100.000 EUR Strafe bei Nichteinhaltung
            </p>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
          Warum BarrierefreiCheck?
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          <FeatureCard
            icon={<SpeedIcon />}
            title="Schnelle Analyse"
            description="Vollständige WCAG 2.1 AA Prüfung Ihrer Website in wenigen Minuten statt Tagen."
          />
          <FeatureCard
            icon={<GermanIcon />}
            title="100% auf Deutsch"
            description="Alle Berichte, Fehlerbeschreibungen und Lösungsvorschläge in deutscher Sprache."
          />
          <FeatureCard
            icon={<BFSGIcon />}
            title="BFSG-Mapping"
            description="Direkte Zuordnung zu den gesetzlichen BFSG-Anforderungen für Ihren Compliance-Nachweis."
          />
          <FeatureCard
            icon={<ActionIcon />}
            title="Konkrete Lösungen"
            description="Nicht nur Fehler finden, sondern konkrete Code-Beispiele zur Behebung erhalten."
          />
          <FeatureCard
            icon={<ReportIcon />}
            title="PDF-Berichte"
            description="Professionelle Berichte für Kunden, Geschäftsführung oder Behörden exportieren."
          />
          <FeatureCard
            icon={<PriceIcon />}
            title="Faire Preise"
            description="Ab 49 EUR/Monat - ein Bruchteil der Kosten manueller Audits."
          />
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="bg-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-4">
            Einfache, transparente Preise
          </h2>
          <p className="text-center text-gray-600 mb-12">
            Starten Sie kostenlos und upgraden Sie bei Bedarf
          </p>
          <div className="grid md:grid-cols-4 gap-6">
            <PricingCard
              name="Free"
              price="0"
              features={['5 Seiten pro Scan', '3 Scans/Monat', '1 Domain', 'Basis-Berichte']}
            />
            <PricingCard
              name="Starter"
              price="49"
              features={['100 Seiten pro Scan', '20 Scans/Monat', '1 Domain', 'Vollständige Berichte']}
              highlighted
            />
            <PricingCard
              name="Professional"
              price="99"
              features={['500 Seiten pro Scan', 'Unbegrenzte Scans', '3 Domains', 'API-Zugang']}
            />
            <PricingCard
              name="Agency"
              price="249"
              features={['1.000 Seiten pro Scan', 'Unbegrenzte Scans', '10 Domains', 'White-Label']}
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-blue-600 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Bereit für barrierefreie Websites?
          </h2>
          <p className="text-blue-100 mb-8 text-lg">
            Starten Sie jetzt Ihren ersten kostenlosen Scan
          </p>
          <Link
            to="/register"
            className="inline-block bg-white text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-gray-100 transition-colors"
          >
            Kostenlos registrieren
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <span className="text-xl font-bold text-white">BarrierefreiCheck</span>
              <p className="mt-1 text-sm">BFSG-Compliance leicht gemacht</p>
            </div>
            <div className="flex space-x-6 text-sm">
              <a href="#" className="hover:text-white">Impressum</a>
              <a href="#" className="hover:text-white">Datenschutz</a>
              <a href="#" className="hover:text-white">AGB</a>
              <a href="#" className="hover:text-white">Kontakt</a>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-gray-800 text-center text-sm">
            © 2025 BarrierefreiCheck. Alle Rechte vorbehalten.
          </div>
        </div>
      </footer>
    </div>
  );
};

// Feature Card Component
interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

const FeatureCard: React.FC<FeatureCardProps> = ({ icon, title, description }) => (
  <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 mb-4">
      {icon}
    </div>
    <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
    <p className="text-gray-600">{description}</p>
  </div>
);

// Pricing Card Component
interface PricingCardProps {
  name: string;
  price: string;
  features: string[];
  highlighted?: boolean;
}

const PricingCard: React.FC<PricingCardProps> = ({ name, price, features, highlighted }) => (
  <div
    className={`p-6 rounded-xl ${
      highlighted
        ? 'bg-blue-600 text-white ring-4 ring-blue-300'
        : 'bg-gray-50 text-gray-900'
    }`}
  >
    <h3 className="text-lg font-semibold mb-2">{name}</h3>
    <div className="mb-4">
      <span className="text-3xl font-bold">{price}€</span>
      <span className={highlighted ? 'text-blue-100' : 'text-gray-500'}>/Monat</span>
    </div>
    <ul className="space-y-2 text-sm">
      {features.map((feature, index) => (
        <li key={index} className="flex items-center gap-2">
          <svg className={`h-4 w-4 ${highlighted ? 'text-blue-200' : 'text-green-500'}`} fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          {feature}
        </li>
      ))}
    </ul>
  </div>
);

// Icons
const SpeedIcon = () => (
  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
);

const GermanIcon = () => (
  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
  </svg>
);

const BFSGIcon = () => (
  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

const ActionIcon = () => (
  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
  </svg>
);

const ReportIcon = () => (
  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const PriceIcon = () => (
  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

export default Landing;

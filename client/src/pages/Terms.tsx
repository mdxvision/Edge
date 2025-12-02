import Card from '@/components/ui/Card';

export default function Terms() {
  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Terms of Service</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Last updated: December 2024</p>
      </div>

      <Card className="p-6 prose dark:prose-invert max-w-none">
        <h2>1. Acceptance of Terms</h2>
        <p>
          By accessing and using EdgeBet ("the Platform"), you agree to be bound by these Terms of Service.
          If you do not agree to these terms, you must not use the Platform.
        </p>

        <h2>2. Eligibility</h2>
        <p>
          <strong>You must be at least 21 years of age</strong> to use this Platform. By using the Platform,
          you represent and warrant that you are at least 21 years old and have the legal capacity to enter
          into this agreement.
        </p>
        <p>
          Age verification is mandatory. You will be required to provide your date of birth and confirm
          that you meet the age requirement before accessing certain features.
        </p>

        <h2>3. Platform Purpose - SIMULATION ONLY</h2>
        <p className="text-red-600 dark:text-red-400 font-semibold">
          IMPORTANT: EdgeBet is an EDUCATIONAL and SIMULATION platform only.
        </p>
        <ul>
          <li>No real money wagering occurs through this Platform</li>
          <li>All betting recommendations are for educational purposes only</li>
          <li>The Platform simulates sports betting analytics and DFS lineup optimization</li>
          <li>You should NOT place actual bets based solely on recommendations from this Platform</li>
          <li>We do not accept deposits or process any real money transactions</li>
        </ul>

        <h2>4. Account Security</h2>
        <p>
          You are responsible for maintaining the confidentiality of your account credentials. We require:
        </p>
        <ul>
          <li>A strong password (minimum 8 characters)</li>
          <li>Two-factor authentication (2FA) is mandatory for all accounts</li>
          <li>You must not share your account with others</li>
          <li>Report any unauthorized access immediately</li>
        </ul>

        <h2>5. User Conduct</h2>
        <p>You agree not to:</p>
        <ul>
          <li>Use the Platform for any illegal purpose</li>
          <li>Attempt to reverse engineer or exploit the Platform</li>
          <li>Use automated systems to access the Platform without permission</li>
          <li>Interfere with or disrupt the Platform's operation</li>
          <li>Impersonate other users or provide false information</li>
        </ul>

        <h2>6. Intellectual Property</h2>
        <p>
          All content, algorithms, predictions, and analytics on this Platform are proprietary to EdgeBet.
          You may not reproduce, distribute, or create derivative works without explicit permission.
        </p>

        <h2>7. No Financial Advice</h2>
        <p>
          The information and recommendations provided by EdgeBet do not constitute financial or gambling advice.
          We are not responsible for any losses you may incur from decisions made based on Platform information.
        </p>

        <h2>8. Disclaimer of Warranties</h2>
        <p>
          The Platform is provided "as is" without any warranties, express or implied. We do not guarantee:
        </p>
        <ul>
          <li>The accuracy of predictions or recommendations</li>
          <li>Uninterrupted access to the Platform</li>
          <li>That the Platform will be free of errors or bugs</li>
          <li>Any specific financial outcomes</li>
        </ul>

        <h2>9. Limitation of Liability</h2>
        <p>
          EdgeBet and its operators shall not be liable for any direct, indirect, incidental, special,
          or consequential damages arising from your use of the Platform, including any financial losses
          from betting decisions.
        </p>

        <h2>10. Data Privacy</h2>
        <p>
          We collect and process your data as described in our Privacy Policy. By using the Platform,
          you consent to our data practices.
        </p>

        <h2>11. Account Termination</h2>
        <p>
          We reserve the right to suspend or terminate your account at any time for violation of these
          terms or for any other reason at our sole discretion.
        </p>

        <h2>12. Changes to Terms</h2>
        <p>
          We may modify these terms at any time. Continued use of the Platform after changes constitutes
          acceptance of the modified terms.
        </p>

        <h2>13. Governing Law</h2>
        <p>
          These terms shall be governed by and construed in accordance with applicable laws, without
          regard to conflict of law principles.
        </p>

        <h2>14. Contact Information</h2>
        <p>
          For questions about these Terms of Service, please contact support through the Platform.
        </p>
      </Card>

      <Card className="p-6 border-warning-200 dark:border-warning-500/30 bg-warning-50/50 dark:bg-warning-500/10">
        <p className="text-warning-700 dark:text-warning-300 text-sm">
          <strong>Reminder:</strong> This is an educational simulation platform. Do not make real gambling
          decisions based solely on the predictions and recommendations provided here. Always gamble
          responsibly and within your means if you choose to participate in actual sports betting.
        </p>
      </Card>
    </div>
  );
}

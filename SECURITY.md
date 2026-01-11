# Security Policy

## Project Status

namel3ss is currently in **alpha** (v0.1.0a7). While we take security seriously, please note that the project is not yet production-ready and may contain security vulnerabilities.

## Supported Versions

| Version | Status | Security Support |
| ------- | ------ | ---------------- |
| 0.1.x   | Alpha  | :white_check_mark: Best effort |
| < 0.1.0 | Deprecated | :x: No support |

**Note**: Once namel3ss reaches beta or stable release, this table will be updated with specific version support commitments.

## Reporting a Vulnerability

If you discover a security issue, please report it **privately** via email:

**Email**: info@namel3ss.com

### What to Include

Please provide the following information in your report:

1. **Description**: Clear explanation of the vulnerability
2. **Impact**: Potential security impact and affected components
3. **Reproduction Steps**: Detailed steps to reproduce the issue
4. **Environment**: Version, OS, Python version, and relevant configuration
5. **Proof of Concept**: Code or configuration demonstrating the issue (if applicable)
6. **Suggested Fix**: Your recommendations for remediation (optional but appreciated)

### Response Timeline

We aim to respond according to the following timeline:

- **Initial Response**: Within 48 hours of receipt
- **Triage and Assessment**: Within 7 days
- **Status Updates**: Every 7 days until resolution
- **Fix Timeline**: Varies based on severity (see below)

### Severity Levels

| Severity | Description | Target Fix Timeline |
| -------- | ----------- | ------------------- |
| **Critical** | Remote code execution, authentication bypass, data breach | 7 days |
| **High** | Privilege escalation, significant data exposure | 14 days |
| **Medium** | Limited information disclosure, DoS vulnerabilities | 30 days |
| **Low** | Minor issues with limited impact | 60 days |

**Note**: These are target timelines for alpha releases. Production releases will have stricter SLAs.

## Disclosure Policy

We follow **coordinated disclosure**:

1. Security issues are fixed privately
2. Fixes are released as soon as possible
3. Public disclosure occurs after:
   - A fix is available
   - Users have had reasonable time to update (typically 7-14 days)
   - Or 90 days have passed since initial report (whichever comes first)

We will credit reporters in release notes unless they prefer to remain anonymous.

## Security Best Practices for Users

### For Development

1. **Keep Dependencies Updated**: Regularly update namel3ss and all dependencies
2. **Use Virtual Environments**: Isolate namel3ss installations using Python virtual environments
3. **Validate Packages**: Always run `n3 pkg verify` before installing third-party packages
4. **Review Package Manifests**: Check `capsule.ai` exports and LICENSE files in packages
5. **Secure Secrets**: Use environment variables or `.env` files (never commit secrets)

### For AI Provider Integration

1. **API Key Security**: Store API keys in environment variables, not in `.ai` files
2. **Rate Limiting**: Implement rate limiting for AI calls in production
3. **Input Validation**: Validate all user inputs before passing to AI providers
4. **Output Sanitization**: Sanitize AI outputs before displaying to users
5. **Provider Selection**: Use trusted, tier-1 AI providers (OpenAI, Anthropic, Ollama)

### For Memory and State

1. **Data Encryption**: Encrypt sensitive data in memory stores
2. **Access Control**: Implement proper authentication for Studio in production
3. **Audit Logging**: Enable memory operation logging for compliance
4. **Data Retention**: Define and enforce data retention policies
5. **Backup Security**: Secure database backups with encryption

### For Production Deployment

1. **Network Security**: Use HTTPS/TLS for all network communications
2. **Database Security**: Use strong passwords and restrict database access
3. **Environment Isolation**: Separate development, staging, and production environments
4. **Monitoring**: Implement security monitoring and alerting
5. **Regular Audits**: Conduct regular security audits and penetration testing

**Note**: Full production deployment guidelines are available in `docs/production-deployment.md` (to be created).

## Known Security Considerations

### Alpha Status Limitations

- **Breaking Changes**: Security fixes may introduce breaking changes in alpha
- **Limited Testing**: Security testing is ongoing; not all attack vectors have been evaluated
- **Third-party Dependencies**: Security depends on upstream Python packages
- **AI Provider Security**: Security is partially dependent on external AI provider security

### Current Security Features

- ✅ **Deterministic Execution**: Reduces attack surface through predictable behavior
- ✅ **Explicit AI Boundary**: AI calls are traceable and auditable
- ✅ **Package Verification**: Checksum and license validation for packages
- ✅ **Memory Governance**: Explicit, inspectable memory operations
- ✅ **Input Validation**: Type checking and constraint validation in runtime

### Planned Security Enhancements (Beta/v1.0)

- [ ] Security audit by third-party firm
- [ ] Formal threat modeling
- [ ] Automated security scanning in CI/CD
- [ ] Security-focused documentation
- [ ] CVE tracking and disclosure process
- [ ] Security bug bounty program (post-v1.0)

## Security-Related Configuration

### Environment Variables

Sensitive configuration should use environment variables:

```bash
# AI Provider Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database (Production)
N3_DATABASE_URL=postgres://user:pass@host:5432/db
N3_PERSIST_TARGET=postgres

# Studio Access (Production)
N3_STUDIO_AUTH_ENABLED=true
N3_STUDIO_AUTH_TOKEN=<secure-random-token>
```

### Secure Defaults

namel3ss uses secure defaults:

- SQLite databases are created with restrictive permissions
- Studio binds to `localhost` by default (not `0.0.0.0`)
- Temporary files are created in user-specific directories
- Python tool execution uses isolated subprocesses

## Reporting Other Issues

**Security vulnerabilities**: info@namel3ss.com (private)  
**Bugs and issues**: [GitHub Issues](https://github.com/namel3ss-Ai/namel3ss/issues)  
**General questions**: [GitHub Discussions](https://github.com/namel3ss-Ai/namel3ss/discussions)

## Contact

For security-related questions or concerns:

- **Email**: info@namel3ss.com
- **Subject Line**: Please use `[SECURITY]` prefix for security reports

**Do not open public issues for security vulnerabilities.**

---

*Last Updated: 2026-01-11*  
*Security Policy Version: 1.0*

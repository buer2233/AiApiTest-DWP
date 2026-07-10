import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.SecurityRealm
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.nio.file.StandardCopyOption
import java.nio.file.attribute.PosixFilePermissions
import java.util.logging.Logger
import jenkins.model.Jenkins


Jenkins jenkins = Jenkins.get()
def realm = jenkins.getSecurityRealm()
if (!(realm instanceof HudsonPrivateSecurityRealm) && realm != SecurityRealm.NO_AUTHENTICATION) {
  Logger.getLogger('aiapitest.local-api-token').warning(
    'Skip local API token bootstrap because Jenkins uses a non-local security realm.'
  )
  return
}

String username = 'codex_api'
String tokenName = 'aiapitest-local-acceptance'
Path credentialPath = Paths.get('/var/jenkins_home/aiapitest-local-api-token.txt')
def ownerOnlyPermissions = PosixFilePermissions.fromString("rw-------")
def user = hudson.model.User.getById(username, true)
def property = user.getProperty(jenkins.security.ApiTokenProperty.class)

def revokeDuplicateTokens = { String keepUuid ->
  property.tokenStore.getTokenListSortedByName()
    .findAll { token -> token.name == tokenName && token.uuid != keepUuid }
    .each { token -> property.tokenStore.revokeToken(token.uuid) }
}

if (Files.isRegularFile(credentialPath) && Files.size(credentialPath) > 0) {
  String[] credentialParts = Files.readString(credentialPath).trim().split(':', 2)
  if (credentialParts.length == 2 && credentialParts[0] == username && credentialParts[1]) {
    def matchedToken = property.tokenStore.findMatchingToken(credentialParts[1])
    if (matchedToken != null && matchedToken.name == tokenName) {
      revokeDuplicateTokens(matchedToken.uuid)
      Files.setPosixFilePermissions(credentialPath, ownerOnlyPermissions)
      user.save()
      jenkins.save()
      return
    }
  }
}

revokeDuplicateTokens(null)
def result = property.tokenStore.generateNewToken(tokenName)
Path temporaryPath = Files.createTempFile(credentialPath.parent, '.aiapitest-local-api-token-', '.tmp')
try {
  Files.write(temporaryPath, (username + ':' + result.plainValue).getBytes('UTF-8'))
  Files.setPosixFilePermissions(temporaryPath, ownerOnlyPermissions)
  Files.move(
    temporaryPath,
    credentialPath,
    StandardCopyOption.ATOMIC_MOVE,
    StandardCopyOption.REPLACE_EXISTING,
  )
  Files.setPosixFilePermissions(credentialPath, ownerOnlyPermissions)
} finally {
  Files.deleteIfExists(temporaryPath)
}
user.save()
jenkins.save()

import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.Path
import java.nio.file.Paths

// 仅迁移历史遗留的单个 init 脚本，避免影响 Jenkins home 中的其他文件。
Path legacyInitScript = Paths.get(
    "/var/jenkins_home/init.groovy.d/configure-local-mounted-jobs.groovy"
)

if (
    Files.isRegularFile(legacyInitScript, LinkOption.NOFOLLOW_LINKS) &&
    !Files.isSymbolicLink(legacyInitScript)
) {
    Files.deleteIfExists(legacyInitScript)
    println("[aiapitest] retired legacy local jobs init script")
} else {
    println("[aiapitest] legacy local jobs init migration skipped")
}

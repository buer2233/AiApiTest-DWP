#!/usr/bin/env sh
# Git 仅通过此 helper 向受控远端读取 Jenkins 注入的用户名或密码，禁止输出调试信息。
case "$1" in
  *[Uu]sername*) printf '%s\n' "$CATALOG_GIT_PUSH_USERNAME" ;;
  *) printf '%s\n' "$CATALOG_GIT_PUSH_PASSWORD" ;;
esac

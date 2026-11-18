on run {daemon_file, agent_file, user}

  set prefs_dir to "/Users/" & user & "/Library/Preferences/com.carriez.RustDesk/"
  set prefs_toml to quoted form of (prefs_dir & "RustDesk.toml")
  set prefs2_toml to quoted form of (prefs_dir & "RustDesk2.toml")
  set daemon_plist_q to quoted form of "/Library/LaunchDaemons/com.carriez.RustDesk_service.plist"
  set agent_plist_q to quoted form of "/Library/LaunchAgents/com.carriez.RustDesk_server.plist"
  set root_prefs_q to quoted form of "/var/root/Library/Preferences/com.carriez.RustDesk/"
  set daemon_target_q to quoted form of "system/com.carriez.RustDesk_service"

  set sh1 to "echo " & quoted form of daemon_file & " > " & daemon_plist_q & " && chown root:wheel " & daemon_plist_q & ";"

  set sh2 to "echo " & quoted form of agent_file & " > " & agent_plist_q & " && chown root:wheel " & agent_plist_q & ";"

  set sh3 to "cp -rf " & prefs_toml & " " & root_prefs_q & ";"

  set sh4 to "cp -rf " & prefs2_toml & " " & root_prefs_q & ";"

  set sh5 to "launchctl bootout " & daemon_target_q & " 2>/dev/null || launchctl unload -w " & daemon_plist_q & " 2>/dev/null || true; launchctl bootstrap system " & daemon_plist_q & " 2>/dev/null || launchctl load -w " & daemon_plist_q & ";"

  set sh to sh1 & sh2 & sh3 & sh4 & sh5

  do shell script sh with prompt "RustDesk wants to install daemon and agent" with administrator privileges
end run

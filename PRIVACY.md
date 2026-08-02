# Privacy

3D Print Uploader stores configuration, Google OAuth credentials, login tokens,
upload history, and logs locally on the current user's device. These files are
not included in the source repository or release packages.

The application connects to Google only when authenticating or using Google
Drive. Beacons.ai opens in the user's regular Chrome browser; the application
does not collect or transmit Beacons passwords.

Every user must import their own Google Desktop-app OAuth `credentials.json`.
Never publish `credentials.json`, `token.json`, `config.json`, `history.json`,
or `app.log`.

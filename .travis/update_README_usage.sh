original_README=$(cat README.rst)

(head -n $(read -d : <<< $(less README.rst | grep ".. BEGIN USAGE" -n); expr $REPLY + 1) README.rst; \
printf ".. code-block:: shell\n\n    cpac --help\n"; \
cpac --help | sed 's/^/    /'; \
tail --lines=+$(read -d : <<< $(less README.rst | grep ".. END USAGE" -n); expr $REPLY - 1) README.rst\
) > tempREADME
mv tempREADME README.rst

if [ "$(cat README.rst)" = "$original_README" ]; then
    original_ORIGIN=$(git remote get-url origin)
    git remote remove origin
    git remote add origin $"https://${GITHUB_PUSH_TOKEN}@"$(read -d @ <<< $(echo $original_ORIGIN | rev); echo $REPLY | rev)
    git add README.rst
    git commit -m ":books: Update usage from helpstring"
    git push origin $(git rev-parse --abbrev-ref HEAD)
fi
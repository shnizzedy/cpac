original_README=$(cat README.rst)

(head -n $(read -d : <<< $(less README.rst | grep ".. BEGIN USAGE" -n); expr $REPLY + 1) README.rst; \
printf ".. code-block:: shell\n\n    cpac --help\n"; \
cpac --help | sed 's/^/    /'; \
tail --lines=+$(read -d : <<< $(less README.rst | grep ".. END USAGE" -n); expr $REPLY - 1) README.rst\
) > tempREADME
mv tempREADME README.rst &
wait %1

if [ "$(cat README.rst)" = "$original_README" ]; then
    git remote set-url origin $"https://${GITHUB_USERNAME}:${GITHUB_PUSH_TOKEN}@github.com/"${$(git remote get-url origin):19}
    git add README.rst
    git commit -m ":books: Update usage from helpstring"
    git push origin $TRAVIS_BRANCH
fi
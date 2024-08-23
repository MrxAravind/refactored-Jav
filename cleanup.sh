git checkout --orphan new-branch
git add -A
git commit -m "Action Update"
git branch -D main
git branch -m main
git push -f origin main
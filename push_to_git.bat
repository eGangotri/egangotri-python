set timestamp=%DATE:/=-%_%TIME::=-%
set timestamp=%timestamp: =%
set arg1=%1
set arg1WithoutQuotes=%arg1:"='%
set commit_msg="Optimizations at %timestamp% %arg1WithoutQuotes%"
git status
git add *.py
git add *.md
git add *.txt
git add *.json
git add *.bat
git add *.yaml
git commit -m %commit_msg%
git push origin master
git status


cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox
# Confirm removal of embedded .git directory
Remove-Item -Recurse -Force phase4_tts/Chatterbox-TTS-Extended/.git -ErrorAction SilentlyContinue
# Create .gitignore to exclude large files
echo "filelist_new.txt" > .gitignore
echo "*.pdf" >> .gitignore
echo "audio_chunks/" >> .gitignore
echo "artifacts/" >> .gitignore
echo "phase3-chunking/src/phase3_chunking/chunks/" >> .gitignore
echo "phase7_batch/chunks/" >> .gitignore
echo "*.log" >> .gitignore
echo "*.db" >> .gitignore
# Stage and commit changes, including .gitignore
git add .gitignore
git add .
git commit -m "Add .gitignore and finalize submodule setup"
# Rename branch to main
git branch -m master main
# Push to GitHub
git push -u origin main
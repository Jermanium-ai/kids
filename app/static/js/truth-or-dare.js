/**
 * PlaySync - Truth or Dare Challenge Mode
 * Mature but not explicit, gender-neutral questions
 */

const TRUTH_QUESTIONS = [
    "What's the most embarrassing thing you've done in front of others?",
    "Have you ever lied to someone close to you? What about?",
    "What's something you'd never want your family to know about you?",
    "Have you ever texted someone and regretted it immediately?",
    "What's a skill you wish you were better at?",
    "What's the worst advice you've ever given someone?",
    "Have you ever stalked someone on social media?",
    "What's a weird habit you have that nobody knows about?",
    "When was the last time you genuinely cried?",
    "Have you ever acted like you understood something when you didn't?",
    "What's a purchase you regret spending money on?",
    "Have you ever ghosted someone? Why?",
    "What's the pettiest thing you've ever been upset about?",
    "Have you ever judged someone by their appearance?",
    "What's the most controversial opinion you secretly hold?",
    "Have you ever taken credit for someone else's work?",
    "What's something you do differently when people are watching?",
    "Have you ever broken a promise to someone important?",
    "What's the most childish thing you still enjoy doing?",
    "Have you ever been genuinely afraid of someone you know?"
];

const DARE_CHALLENGES = [
    "Send a funny selfie to the group chat (if available)",
    "Do an impression of your opponent for 30 seconds",
    "Describe your opponent in 3 compliments without laughing",
    "Speak in a funny accent for the next 2 minutes",
    "Do 10 push-ups or jumping jacks right now",
    "Call someone and sing them 'Happy Birthday' (fake birthday if needed)",
    "Walk around the room like a penguin for 30 seconds",
    "Do your best dance move",
    "Recite the alphabet backwards as fast as you can",
    "Try to make your opponent smile/laugh without talking",
    "Post a funny caption about this game on your social media",
    "Eat a spoonful of something unusual from your kitchen",
    "Do a funny TikTok dance (if you know one)",
    "Compliment your opponent's outfit in an exaggerated way",
    "Switch clothes with your opponent for one game",
    "Tell a terrible joke and pretend it's hilarious",
    "Imitate your opponent's way of speaking for 5 minutes",
    "Do a silly version of a exercise (exaggerated stretching, etc)",
    "Write a poem about losing to your opponent",
    "Challenge your opponent to arm wrestle (loser does another dare)"
];

class TruthOrDareModal {
    constructor() {
        this.currentQuestion = null;
    }

    showChallenge(loserName, isLoser) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black/70 flex items-center justify-center z-[9999] animate-fade-in overflow-y-auto p-4';
        modal.id = 'tod-modal';
        modal.style.display = 'flex';
        
        const choice = Math.random() > 0.5 ? 'truth' : 'dare';
        const question = choice === 'truth' 
            ? TRUTH_QUESTIONS[Math.floor(Math.random() * TRUTH_QUESTIONS.length)]
            : DARE_CHALLENGES[Math.floor(Math.random() * DARE_CHALLENGES.length)];
        
        this.currentQuestion = question;
        
        const titleText = isLoser ? `${loserName}, it's time for...` : `Challenge for ${loserName}...`;
        const choiceEmoji = choice === 'truth' ? '🤔' : '🎭';
        const choiceLabel = choice === 'truth' ? 'TRUTH' : 'DARE';
        
        modal.innerHTML = `
            <div class="bg-gradient-to-br from-purple-900 via-slate-900 to-slate-800 rounded-2xl p-6 md:p-8 max-w-md w-full space-y-6 border-2 border-purple-500 my-auto">
                <div class="text-center">
                    <p class="text-xs md:text-sm text-slate-400 mb-2">${titleText}</p>
                    <div class="text-5xl md:text-6xl mb-4">${choiceEmoji}</div>
                    <div class="text-2xl md:text-3xl font-bold text-purple-400">${choiceLabel}</div>
                </div>
                
                <div class="bg-slate-700/50 rounded-lg p-4 border border-purple-400/30 min-h-24 flex items-center">
                    <p class="text-base md:text-lg text-center font-semibold text-white">${question}</p>
                </div>
                
                <div class="flex flex-col md:flex-row gap-2 md:gap-3">
                    <button class="flex-1 bg-green-600 hover:bg-green-500 px-4 py-3 rounded-lg font-bold transition-all transform hover:scale-105 tod-accept">
                        Done! 💪
                    </button>
                    <button class="flex-1 bg-orange-600 hover:bg-orange-500 px-4 py-3 rounded-lg font-bold transition-all transform hover:scale-105 tod-another">
                        Another! 🔄
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Event listeners
        modal.querySelector('.tod-accept').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('.tod-another').addEventListener('click', () => {
            modal.remove();
            // Show another challenge after short delay
            setTimeout(() => {
                this.showChallenge(loserName, isLoser);
            }, 300);
        });
    }
}

window.TruthOrDareModal = TruthOrDareModal;

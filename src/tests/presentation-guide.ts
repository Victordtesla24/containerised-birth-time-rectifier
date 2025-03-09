import * as readline from 'readline';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * This script guides you through presenting the test results to stakeholders.
 * It provides step-by-step instructions and runs the appropriate commands at each step.
 */

// Create readline interface
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Define presentation steps
const steps = [
  {
    title: 'Introduction',
    description: 'Begin by introducing the purpose of this presentation: demonstrating the quality, performance, and polish of our UI/UX enhancements.',
    action: null
  },
  {
    title: 'Testing Approach Overview',
    description: 'Explain our comprehensive testing approach covering visual regression, performance, compatibility, interaction, and visual quality testing.',
    action: async () => {
      await execAsync('cat docs/testing-strategy.md | head -30');
    }
  },
  {
    title: 'Test Categories',
    description: 'Show the different test categories and test files we\'ve implemented.',
    action: async () => {
      await execAsync('npm run test:all');
    }
  },
  {
    title: 'Visual Regression Tests',
    description: 'Explain how visual regression tests ensure our components render correctly and consistently.',
    action: async () => {
      await execAsync('npm run test:visual');
    }
  },
  {
    title: 'Performance Tests',
    description: 'Discuss how performance tests verify smooth animations and efficient rendering.',
    action: async () => {
      await execAsync('npm run test:performance');
    }
  },
  {
    title: 'Compatibility Tests',
    description: 'Explain how compatibility tests ensure the application works across different browsers and devices.',
    action: async () => {
      await execAsync('npm run test:compatibility');
    }
  },
  {
    title: 'Interaction Tests',
    description: 'Describe how interaction tests verify that user interactions work correctly.',
    action: async () => {
      await execAsync('npm run test:interaction');
    }
  },
  {
    title: 'Visual Quality Tests',
    description: 'Explain how visual quality tests verify the high quality of our shaders, materials, and visual effects.',
    action: async () => {
      await execAsync('npm run test:quality');
    }
  },
  {
    title: 'Test Report',
    description: 'Show the comprehensive test report with visual evidence and metrics.',
    action: async () => {
      await execAsync('npm run test:report');
    }
  },
  {
    title: 'Live Demo',
    description: 'Demonstrate the application live to show the UI/UX enhancements in action.',
    action: async () => {
      console.log('\nLaunching the application for live demo...');
      console.log('In a new terminal window, run: npm run dev');
      console.log('Then navigate to http://localhost:3000 in your browser');
    }
  },
  {
    title: 'Conclusion',
    description: 'Conclude the presentation by summarizing the key quality aspects and achievements.',
    action: null
  }
];

// Function to prompt for next step
function promptNextStep(index: number) {
  if (index >= steps.length) {
    console.log('\n🎉 Presentation complete! Thank you for attending.\n');
    rl.close();
    return;
  }

  const step = steps[index];

  console.log('\n' + '='.repeat(80));
  console.log(`Step ${index + 1}/${steps.length}: ${step.title}`);
  console.log('='.repeat(80));
  console.log(`\n${step.description}\n`);

  if (step.action) {
    rl.question('Press Enter to run this step (or type "skip" to skip): ', async (answer) => {
      if (answer.toLowerCase() !== 'skip') {
        try {
          console.log('\n' + '-'.repeat(40) + ' OUTPUT ' + '-'.repeat(40) + '\n');
          await step.action();
          console.log('\n' + '-'.repeat(40) + ' END OUTPUT ' + '-'.repeat(39) + '\n');
        } catch (error) {
          console.error('Error executing step:', error);
        }
      }

      rl.question('Press Enter to continue to the next step: ', () => {
        promptNextStep(index + 1);
      });
    });
  } else {
    rl.question('Press Enter to continue to the next step: ', () => {
      promptNextStep(index + 1);
    });
  }
}

// Start presentation
async function startPresentation() {
  console.log('\n' + '*'.repeat(80));
  console.log('*' + ' '.repeat(25) + 'STAKEHOLDER PRESENTATION GUIDE' + ' '.repeat(25) + '*');
  console.log('*' + ' '.repeat(18) + 'UI/UX ENHANCEMENTS TESTING RESULTS' + ' '.repeat(19) + '*');
  console.log('*'.repeat(80) + '\n');

  console.log('This guide will walk you through presenting the testing results of the UI/UX enhancements');
  console.log('to stakeholders. It provides step-by-step instructions and runs the appropriate');
  console.log('commands at each step.\n');

  // Verify setup before starting
  try {
    console.log('Verifying testing setup...');
    await execAsync('npm run test:verify-setup');

    rl.question('\nPress Enter to begin the presentation: ', () => {
      promptNextStep(0);
    });
  } catch (error) {
    console.error('Error verifying setup:', error);
    console.log('\nPlease fix the setup issues before starting the presentation.');
    rl.close();
  }
}

// Handle exit
rl.on('close', () => {
  console.log('\nExiting presentation guide. Goodbye!');
  process.exit(0);
});

// Start the presentation
startPresentation().catch(error => {
  console.error('Error starting presentation:', error);
  rl.close();
  process.exit(1);
});

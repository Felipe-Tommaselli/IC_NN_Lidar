import matplotlib.pyplot as plt

# Sample data for training and validation loss
epochs = list(range(1, 21))
training_loss = [0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.18, 0.15, 0.12, 0.1, 0.08, 0.07, 0.06, 0.05, 0.04, 0.035, 0.03, 0.025, 0.02, 0.018]
validation_loss = [0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.33, 0.3, 0.28, 0.26, 0.25, 0.24, 0.23, 0.22, 0.21, 0.2, 0.19, 0.18, 0.17, 0.16]

# Convergence final errors for training and validation
final_training_loss = training_loss[-1]
final_validation_loss = validation_loss[-1]

# Plotting training and validation loss
plt.plot(epochs, training_loss, label='Training Loss', marker='o')
plt.plot(epochs, validation_loss, label='Validation Loss', marker='o')

# Adding labels and title
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.title('Learning Loss Plot (L1 Loss)\nFinal Training Loss: {:.4f}'.format(final_training_loss))

# Adding legend
plt.legend()

# Adjusting layout for better visualization
plt.tight_layout()

# Show the plot
plt.show()

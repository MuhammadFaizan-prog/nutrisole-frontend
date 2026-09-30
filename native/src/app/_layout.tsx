import { Slot } from 'expo-router';
import App from '../../App';
// Shared screen and sheet state remain mounted while Expo Router owns navigation.
export default function RootLayout() { return <App><Slot /></App>; }

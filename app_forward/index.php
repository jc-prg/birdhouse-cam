<?php
// File: index.php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

// File to store the IPv6 address and birdhouse identifier
$ipv6_file = 'ipv6_address.txt';

// Function to get the stored IPv6 addresses and birdhouse identifiers
function getStoredIPv6Addresses($file) {
    if (file_exists($file)) {
        $contents = file_get_contents($file);
        if ($contents !== false) {
            return json_decode($contents, true);
        }
    }
    return [];
}

// Function to save the IPv6 address and birdhouse identifier to file
function saveIPv6Address($file, $ipv6, $birdhouse_identifier) {
    $stored_addresses = getStoredIPv6Addresses($file);
    $stored_addresses[$birdhouse_identifier] = $ipv6;
    file_put_contents($file, json_encode($stored_addresses));
}

// Check if script is called with parameter to identify and save IPv6 address
if (isset($_GET['identify_ipv6']) && isset($_GET['identify_birdhouse'])) {
    // Get the IPv6 address and birdhouse identifier from the HTTP request
    $client_ipv6 = $_GET['identify_ipv6'];
    $birdhouse_identifier = $_GET['identify_birdhouse'];

    // Save the IPv6 address and birdhouse identifier to file
    saveIPv6Address($ipv6_file, $client_ipv6, $birdhouse_identifier);
    exit; // Stop script execution after saving IPv6 address
}

// Get the stored IPv6 addresses and birdhouse identifiers
$stored_addresses = getStoredIPv6Addresses($ipv6_file);

// If no stored addresses, display message
if (empty($stored_addresses)) {
    echo '<!DOCTYPE html>
    <html>
    <head>
        <!-- Add your head content here -->
    </head>
    <body style="background:#111111">
        <center>
            <h1 style="color:#EEEEEE">jc://birdhouse/</h1>
            <br/>&nbsp;
            <p style="color:#EEEEEE">
                Got no data from birdhouse server yet.
            </p>
        </center>
    </body>
    </html>';
} else {
    // Display links with stored data
    echo '<!DOCTYPE html>
    <html>
    <head>
        <!-- Add your head content here -->
    </head>
    <body style="background:#111111">
        <center>
            <h1 style="color:#EEEEEE">jc://birdhouse/</h1>
            <br/>&nbsp;';

    // Loop through each entry in the data and display links
    echo '<p style="color:#EEEEEE">
        <img src="bird.gif" style="width:250px;" /><br/>
        <br/>&nbsp;<ol style="color:#EEEEEE">';
    foreach ($stored_addresses as $birdhouse_identifier => $ipv6_address) {
        echo '<li style="color:#EEEEEE">
            Click here: <a href="http://[' . $ipv6_address . ']:8000" style="color:yellow">Birdhouse ' . $birdhouse_identifier . '</a>.<br/>&nbsp;
            <img src="http://[' . $ipv6_address . ']:8007/lowres/stream.mjpg?cam1?' . $birdhouse_identifier . '?' . $birdhouse_identifier . '"  style="border:1px solid white;margin:8px;"/><br/>&nbsp;<br/>&nbsp;
        </li>';
    }
    echo "</ol></p>";

    echo '</center>
    </body>
    </html>';
}
?>

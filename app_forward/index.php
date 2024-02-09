<?php
// File: index.php


// File to store the IPv6 address
$ipv6_file = 'ipv6_address.txt';

// Function to get the stored IPv6 address
function getStoredIPv6Address($file) {
    if (file_exists($file)) {
        return file_get_contents($file);
    }
    return false;
}

// Function to save the IPv6 address to file using fwrite
function saveIPv6Address_2($file, $ipv6) {
    $handle = fopen($file, 'w'); // Open the file for writing (truncate existing content)
    if ($handle !== false) {
        fwrite($handle, $ipv6); // Write the IPv6 address to the file
        fclose($handle); // Close the file handle
        return true;
    }
    return false; // Return false if file opening fails
}

// Function to save the IPv6 address to file
function saveIPv6Address($file, $ipv6) {
    //echo iswriteable($file) ? "is writable<br>" : "not writable<br>";
    return file_put_contents($file, $ipv6);
}

// Check if script is called with parameter to identify and save IPv6 address
if (isset($_GET['identify_ipv6'])) {
    // Get the IPv6 address from the HTTP request
    //echo ".";
    $client_ipv6 = $_GET['identify_ipv6'];
    if (saveIPv6Address($ipv6_file, $client_ipv6)) { echo "OK"; }
    else { echo "Not OK"; }
    echo "  ";
    echo $client_ipv6;

    // Save the IPv6 address to file
    if (filter_var("[$client_ipv6]", FILTER_VALIDATE_IP, FILTER_FLAG_IPV6)) {
        echo 'IPv6 address saved successfully!';
        saveIPv6Address($ipv6_file, $client_ipv6);
    } else {
        echo 'Invalid IPv6 address' + $client_ipv6;
    }
    echo "end";
    exit; // Stop script execution after saving IPv6 address
}

// Get the stored IPv6 address
$ipv6_address = getStoredIPv6Address($ipv6_file);

// If IPv6 address is not stored or not accessible, display link
if (!$ipv6_address) { // || !filter_var("[$ipv6_address]", FILTER_VALIDATE_IP, FILTER_FLAG_IPV6)) {
    echo '<!DOCTYPE html>
    <html>
    <head>
        <title>Access Server</title>
    </head>
    <body>
        <h1>Welcome to the Server Access Portal</h1>
        <p>
            To access the server, please click the link below:
            <a href="http://[<YOUR_IPV6_ADDRESS>]:8000">Click here to access server</a>
        </p>
    </body>
    </html>';
} else {
    // Display link with stored IPv6 address
    echo '<!DOCTYPE html>
    <html>
    <head>
        <title>Access Server</title>
    </head>
    <body>
        <h1>Welcome to the Server Access Portal</h1>
        <p>
            To access the server, please click the link below:
            <a href="http://[' . $ipv6_address . ']:8000">Click here to access server</a>
        </p>
    </body>
    </html>';
}
?>
